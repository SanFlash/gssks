"""Login, cooldown, session invalidation, and single-use password resets."""

from datetime import timedelta
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    current_app,
    jsonify,
    abort,
)
from flask_wtf.csrf import generate_csrf
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import check_password_hash, generate_password_hash
from app.extensions import db, limiter
from app.models import User, now
from app.forms import LoginForm, ForgotForm, ResetForm
from app.utils.security import audit
from app.services.email import queue_email

auth_bp = Blueprint("auth", __name__)
DUMMY_HASH = generate_password_hash("unusable-timing-comparison-password")


@auth_bp.route("/login", methods=["GET", "POST"])
@auth_bp.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("10 per minute; 60 per hour")
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            db.select(User).where(User.email == form.email.data.strip().lower())
        )
        allowed = (
            user
            and user.active
            and not (current_app.config["PRODUCTION"] and user.is_demo)
        )
        locked = user and user.locked_until and user.locked_until > now()
        valid = (
            user.check_password(form.password.data)
            if user
            else check_password_hash(DUMMY_HASH, form.password.data)
        )
        if allowed and not locked and valid:
            session.clear()
            login_user(user)
            session.permanent = True
            user.failed_logins = 0
            user.locked_until = None
            audit("login", "User", user.id)
            db.session.commit()
            if user.can("settings.manage"):
                from app.services.content import settings

                if settings().get("setup_complete") != "true":
                    return redirect(url_for("admin.setup", step=1))
            return redirect(
                url_for("admin.dashboard")
                if user.can("admin.view")
                else url_for("auth.account")
            )
        if user and not locked:
            user.failed_logins += 1
            if user.failed_logins >= 5:
                user.locked_until = now() + timedelta(minutes=15)
                user.failed_logins = 0
        audit("failed login", "User")
        db.session.commit()
        flash(
            "Sign-in failed. Check your credentials or try again after 15 minutes.",
            "error",
        )
    return render_template("auth/login.html", form=form, title="Sign in")


@auth_bp.post("/logout")
@login_required
def logout():
    audit("logout", "User", current_user.id)
    db.session.commit()
    logout_user()
    session.clear()
    return redirect(url_for("public.home"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per minute; 10 per hour")
def forgot():
    form = ForgotForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            db.select(User).where(User.email == form.email.data.lower().strip())
        )
        if (
            user
            and user.active
            and not (current_app.config["PRODUCTION"] and user.is_demo)
        ):
            token = URLSafeTimedSerializer(current_app.secret_key).dumps(
                {"id": user.id, "version": user.session_version}, salt="reset"
            )
            queue_email(
                user.email,
                "Reset your Gyanpath password",
                "reset",
                reset_url=current_app.config["SITE_URL"]
                + url_for("auth.reset", token=token),
            )
            db.session.commit()
        flash(
            "If this account exists, reset instructions have been queued for delivery.",
            "success",
        )
        return redirect(url_for("auth.login"))
    return render_template(
        "public/form.html",
        title="Reset your password",
        form=form,
        intro="Instructions expire after 30 minutes.",
    )


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def reset(token):
    try:
        payload = URLSafeTimedSerializer(current_app.secret_key).loads(
            token, salt="reset", max_age=1800
        )
        user = db.session.get(User, payload["id"])
        if not user or not user.active or user.session_version != payload["version"]:
            raise BadSignature("expired")
    except (BadSignature, SignatureExpired, KeyError):
        flash("This link is invalid, expired, or already used.", "error")
        return redirect(url_for("auth.forgot"))
    form = ResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.locked_until = None
        user.failed_logins = 0
        audit("password reset", "User", user.id)
        db.session.commit()
        session.clear()
        flash("Password updated. Please sign in again.", "success")
        return redirect(url_for("auth.login"))
    return render_template(
        "public/form.html",
        title="Choose a new password",
        form=form,
        intro="Use at least 12 characters.",
    )


@auth_bp.get("/account")
@login_required
def account():
    return render_template("auth/account.html", title="Your account")


@auth_bp.get("/auth/csrf")
@limiter.limit("60 per minute")
def refresh_csrf():
    """Issue a session-bound token without accepting cross-origin access."""
    if request.headers.get("Sec-Fetch-Site") == "cross-site":
        abort(403)
    origin = request.headers.get("Origin")
    if origin and origin.rstrip("/") != request.host_url.rstrip("/"):
        abort(403)
    return jsonify(csrf_token=generate_csrf(), authenticated=current_user.is_authenticated)
