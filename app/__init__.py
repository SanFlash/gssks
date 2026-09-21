"""Application factory and secure defaults."""

import json
import logging
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from flask import (
    Flask,
    request,
    render_template,
    jsonify,
    redirect,
    url_for,
    g,
    has_request_context,
)
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, ProgrammingError
from werkzeug.exceptions import HTTPException
import cloudinary
from app.extensions import db, migrate, login_manager, csrf, cache, limiter, mail
from app.config import configuration, ROOT


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, record):
    if type(connection).__module__.startswith("sqlite3"):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__, instance_path=str(ROOT / "instance"))
    Path(app.instance_path).mkdir(exist_ok=True)
    app.config.update(configuration())
    if test_config:
        app.config.update(test_config)
    if app.config.get("TRUST_PROXY_HOPS", 0):
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(
            app.wsgi_app, x_for=app.config["TRUST_PROXY_HOPS"], x_proto=1
        )
    for extension in [db, login_manager, csrf, cache, limiter, mail]:
        extension.init_app(app)
    migrate.init_app(app, db)
    cloudinary.config(
        cloud_name=app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=app.config["CLOUDINARY_API_KEY"],
        api_secret=app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )
    from app import models
    from app.public import public_bp
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.api import api_bp

    for blueprint in [public_bp, auth_bp, admin_bp, api_bp]:
        app.register_blueprint(blueprint)
    login_manager.login_view = "auth.login"
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(identity):
        try:
            user_id, version = identity.split(":")
            user = db.session.get(models.User, int(user_id))
            if (
                user
                and user.active
                and user.session_version == int(version)
                and not (app.config["PRODUCTION"] and user.is_demo)
            ):
                return user
        except (ValueError, TypeError):
            pass
        return None

    @login_manager.unauthorized_handler
    def unauthorized():
        if request.path.startswith("/api/"):
            return jsonify(error="Authentication required."), 401
        return redirect(url_for("auth.login"))

    @app.before_request
    def readiness_and_maintenance():
        if request.endpoint == "static":
            return None
        if app.config["CONFIGURATION_REQUIRED"]:
            return render_template(
                "errors/configuration.html", title="Configuration required"
            ), 503
        try:
            from app.services.content import settings

            g.site = settings()
        except (OperationalError, ProgrammingError):
            db.session.rollback()
            return render_template(
                "errors/configuration.html", title="Configuration required"
            ), 503
        if g.site.get("maintenance") == "true" and not request.path.startswith(
            ("/admin", "/login", "/logout", "/auth/csrf", "/health", "/api/donations/webhook")
        ):
            if not current_user.is_authenticated or not current_user.can("admin.view"):
                return render_template(
                    "errors/maintenance.html", title="Maintenance"
                ), 503

    @app.get("/health")
    def health():
        db.session.execute(text("SELECT 1"))
        return jsonify(status="ok")

    @app.context_processor
    def common_context():
        if not has_request_context():
            return {}
        from app.services.content import DEFAULTS
        from app.models import SocialLink, NavigationItem
        from app.forms import NewsletterForm
        from app.admin.registry import REGISTRY

        site = getattr(g, "site", DEFAULTS)
        socials, navigation = [], []
        if hasattr(g, "site"):
            socials = db.session.scalars(
                db.select(SocialLink).order_by(SocialLink.id)
            ).all()
            navigation = db.session.scalars(
                db.select(NavigationItem)
                .where(NavigationItem.published.is_(True))
                .order_by(NavigationItem.position)
            ).all()
        return dict(
            site=site,
            socials=socials,
            navigation=navigation,
            newsletter_form=NewsletterForm(formdata=None),
            registry=REGISTRY,
            canonical=app.config["SITE_URL"] + request.path,
            current_year=models.now().year,
            getattr=getattr,
            organization_schema={
                "@context": "https://schema.org",
                "@type": "NGO",
                "name": site["organization_name"],
                "alternateName": "GSSKS",
                "foundingDate": site.get("established", ""),
                "telephone": site.get("phone", ""),
                "email": site.get("email", ""),
                "url": app.config["SITE_URL"],
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": site.get("address", ""),
                    "addressLocality": "Bhopal",
                    "addressRegion": "Madhya Pradesh",
                    "addressCountry": "IN",
                },
            },
        )

    from app.utils.security import rich_text
    from markupsafe import Markup

    app.jinja_env.filters["rich"] = lambda value: Markup(rich_text(value))
    app.jinja_env.filters["inr"] = lambda value: f"₹{(value or 0) / 100:,.2f}"

    @app.template_filter("public_image")
    def public_image(value, width=960):
        value = value or "/static/images/craft.svg"
        parsed = urlsplit(value)
        if (
            parsed.scheme == "https"
            and parsed.hostname == "res.cloudinary.com"
            and "/image/upload/" in parsed.path
            and "/s--" not in parsed.path
        ):
            return value.replace(
                "/image/upload/",
                f"/image/upload/f_auto,q_auto,c_limit,w_{min(max(int(width), 100), 2000)}/",
                1,
            )
        return value

    @app.template_filter("video_embed")
    def video_embed(value):
        parsed = urlsplit(value or "")
        host = parsed.hostname or ""
        ident = ""
        if host in {"www.youtube.com", "youtube.com"}:
            ident = parse_qs(parsed.query).get("v", [""])[0]
        elif host == "youtu.be":
            ident = parsed.path.lstrip("/")
        if ident and __import__("re").fullmatch(r"[A-Za-z0-9_-]{11}", ident):
            return "https://www.youtube-nocookie.com/embed/" + ident
        if host in {"vimeo.com", "www.vimeo.com"} and parsed.path.lstrip("/").isdigit():
            return "https://player.vimeo.com/video/" + parsed.path.lstrip("/")
        return ""

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net https://checkout.razorpay.com https://www.googletagmanager.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; media-src 'self' https://res.cloudinary.com; connect-src 'self' https://api.razorpay.com https://lumberjack.razorpay.com https://cdn.jsdelivr.net https://www.google-analytics.com https://region1.google-analytics.com; frame-src 'self' https://res.cloudinary.com https://api.razorpay.com https://checkout.razorpay.com https://www.youtube-nocookie.com https://player.vimeo.com; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        )
        if app.config["PRODUCTION"]:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        # HTML includes session-bound form tokens, including the public newsletter.
        if response.mimetype == "text/html" or request.path == "/auth/csrf":
            response.headers["Cache-Control"] = "no-store, private"
        if request.path.startswith(
            (
                "/admin",
                "/api",
                "/login",
                "/account",
                "/auth/csrf",
                "/donations",
                "/donation-success",
                "/reset-password",
                "/forgot-password",
            )
        ):
            response.headers["Cache-Control"] = "no-store, private"
            response.headers["X-Robots-Tag"] = "noindex, nofollow"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error=error.description, status=error.code), error.code
        return render_template(
            "errors/error.html",
            title=error.name,
            code=error.code,
            message=error.description,
        ), error.code

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        if request.path.startswith("/api/"):
            return jsonify(
                error="Session expired or CSRF token missing. Refresh and retry."
            ), 400
        app.logger.warning(json.dumps({
            "event": "csrf_rejected", "route": request.endpoint,
            "reason": error.description,
        }))
        return render_template(
            "errors/csrf.html", title="Reopen your form", code=400,
        ), 400

    @app.errorhandler(Exception)
    def unexpected(error):
        db.session.rollback()
        # Log type and route, never exception text that may contain SQL values or personal data.
        app.logger.error(
            json.dumps(
                {
                    "event": "unexpected_error",
                    "type": type(error).__name__,
                    "route": request.endpoint,
                }
            )
        )
        if request.path.startswith("/api/"):
            return jsonify(error="An unexpected error occurred."), 500
        return render_template(
            "errors/error.html",
            title="Something went wrong",
            code=500,
            message="Please try again shortly.",
        ), 500

    from app.cli import register_cli

    register_cli(app)
    return app
