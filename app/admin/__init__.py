"""Permission-checked admin operations and editable content."""

import csv
import io
from collections import Counter
from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    redirect,
    url_for,
    flash,
    Response,
    current_app,
)
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import Optional, Length, Email
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from app import models as m
from app.extensions import db, cache
from app.admin.registry import REGISTRY, PRIVATE_COLUMNS
from app.admin.forms import build_form
from app.utils.security import permission_required, audit, rich_text, safe_url, csv_safe
from app.services.content import settings, DEFAULTS
from app.services.media import MediaService
from app.services.email import queue_email
from app.services.payments import PaymentService, PaymentError

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.before_request
@login_required
def guard():
    if not current_user.can("admin.view"):
        abort(403)


def allowed_resource(resource, action="view"):
    spec = REGISTRY.get(resource)
    if not spec:
        abort(404)
    if not current_user.can(f"{spec[1]}.{action}"):
        abort(403)
    return spec


@admin_bp.get("")
@admin_bp.get("/")
def dashboard():
    cards = []
    for key in [
        "projects",
        "events",
        "volunteers",
        "donations",
        "contacts",
        "artisans",
        "media",
        "documents",
    ]:
        model, prefix, _ = REGISTRY[key]
        if current_user.can(prefix + ".view"):
            cards.append(
                (key, db.session.scalar(db.select(func.count(model.id))), key.title())
            )
    charts = {}
    for key, model, prefix in [
        ("Volunteer registrations", m.VolunteerApplication, "volunteer"),
        ("Event registrations", m.EventRegistration, "event"),
        ("Website enquiries", m.ContactMessage, "contact"),
        ("Monthly donations (₹)", m.Donation, "donation"),
    ]:
        if current_user.can(prefix + ".view"):
            rows = db.session.scalars(
                db.select(model).order_by(model.created_at).limit(10000)
            ).all()
            counts = Counter()
            for r in rows:
                if model is m.Donation and r.status != "Paid":
                    continue
                counts[r.created_at.strftime("%Y-%m")] += (
                    r.amount / 100 if model is m.Donation else 1
                )
            charts[key] = dict(sorted(counts.items())[-12:])
    if current_user.can("project.view"):
        charts["Project distribution"] = dict(
            db.session.execute(
                db.select(m.Project.status, func.count(m.Project.id)).group_by(
                    m.Project.status
                )
            ).all()
        )
    paid = (
        db.session.scalar(
            db.select(func.sum(m.Donation.amount)).where(m.Donation.status == "Paid")
        )
        or 0
        if current_user.can("donation.view")
        else None
    )
    notifications = []
    for key, model, prefix in [
        ("volunteers", m.VolunteerApplication, "volunteer"),
        ("contacts", m.ContactMessage, "contact"),
        ("registrations", m.EventRegistration, "event"),
        ("subscribers", m.NewsletterSubscriber, "subscriber"),
        ("donations", m.Donation, "donation"),
    ]:
        if current_user.can(prefix + ".view"):
            for row in db.session.scalars(
                db.select(model).order_by(model.created_at.desc()).limit(3)
            ):
                notifications.append((row.created_at, key, row.id))
    return render_template(
        "admin/dashboard.html",
        title="Overview",
        cards=cards,
        charts=charts,
        paid=paid,
        notifications=sorted(notifications, reverse=True)[:8],
    )


@admin_bp.get("/manage/<resource>")
def listing(resource):
    model, prefix, fields = allowed_resource(resource)
    query = db.select(model)
    q = request.args.get("q", "").strip()[:100]
    searchable = [
        getattr(model, x)
        for x in ["title", "name", "email", "subject", "action", "tags"]
        if hasattr(model, x)
    ]
    if q and searchable:
        query = query.where(or_(*(c.ilike(f"%{q}%") for c in searchable)))
    status = request.args.get("status", "")[:30]
    if status and hasattr(model, "status"):
        query = query.where(model.status == status)
    if resource == "media":
        for field in ["folder", "resource_type", "visibility"]:
            value = request.args.get(field, "")[:120]
            if value:
                query = query.where(getattr(model, field) == value)
    sort = request.args.get("sort", "newest")
    ordering = model.created_at.asc() if sort == "oldest" else model.created_at.desc()
    if sort == "title" and hasattr(model, "title"):
        ordering = model.title.asc()
    page = db.paginate(
        query.order_by(ordering),
        page=request.args.get("page", 1, type=int),
        per_page=20,
        max_per_page=20,
        error_out=False,
    )
    columns = PRIVATE_COLUMNS.get(resource) or ["id"] + [
        f
        for f in fields
        if f
        in {
            "title",
            "name",
            "email",
            "published",
            "status",
            "value",
            "visibility",
            "folder",
        }
    ]
    return render_template(
        "admin/list.html",
        title=resource.replace("-", " ").title(),
        resource=resource,
        prefix=prefix,
        records=page.items,
        pagination=page,
        fields=fields,
        columns=columns,
        q=q,
    )


@admin_bp.route("/manage/<resource>/new", methods=["GET", "POST"])
@admin_bp.route("/manage/<resource>/<int:record_id>/edit", methods=["GET", "POST"])
def edit(resource, record_id=None):
    model, prefix, fields = allowed_resource(
        resource, "edit" if record_id else "create"
    )
    if not fields or resource == "media" and not record_id:
        abort(405)
    if resource in {"users", "roles"} and current_user.role.name != "SUPER_ADMIN":
        abort(403)
    record = db.get_or_404(model, record_id) if record_id else model()
    form = build_form(model, fields, record if record_id else None)
    if request.method == "GET":
        if resource == "roles" and record_id:
            form.permissions.data = [p.id for p in record.permissions]
        if resource == "blog" and record_id:
            form.tags.data = [p.id for p in record.tags]
    if form.validate_on_submit():
        try:
            if (
                "published" in fields
                and form.published.data != bool(getattr(record, "published", False))
                and not current_user.can(prefix + ".publish")
            ):
                abort(403)
            if (
                resource == "users"
                and record_id == current_user.id
                and (not form.active.data or form.role_id.data != current_user.role_id)
            ):
                raise ValueError("You cannot deactivate or change your own role.")
            if resource == "roles" and record_id and record.name == "SUPER_ADMIN":
                raise ValueError("The SUPER_ADMIN role is protected.")
            for name in fields:
                value = getattr(form, name).data
                col = model.__table__.columns[name]
                if col.foreign_keys:
                    value = value or None
                if name in {
                    "description",
                    "content",
                    "answer",
                    "objectives",
                    "activities",
                    "outcomes",
                    "impact",
                    "products",
                }:
                    value = rich_text(value)
                if name == "email":
                    value = value.strip().lower()
                setattr(record, name, value)
            if resource == "events":
                if record.registration_limit < (record.registration_count or 0):
                    raise ValueError(
                        "Capacity cannot be smaller than the current registration count."
                    )
                if (
                    record.start_time
                    and record.end_time
                    and record.end_time <= record.start_time
                ):
                    raise ValueError("End time must be later than start time.")
            if (
                resource == "projects"
                and record.start_date
                and record.end_date
                and record.end_date < record.start_date
            ):
                raise ValueError("End date must not precede start date.")
            if resource == "documents":
                asset = db.session.get(m.MediaAsset, record.media_id)
                if not asset or asset.resource_type != "raw":
                    raise ValueError("Choose an uploaded PDF document.")
                if record.visibility == "public" and asset.visibility != "public":
                    raise ValueError(
                        "Private media cannot be made public through a document. Upload a public copy."
                    )
            if resource in {"gallery", "project-images"} and getattr(
                record, "media_id", None
            ):
                asset = db.session.get(m.MediaAsset, record.media_id)
                if (
                    not asset
                    or asset.visibility != "public"
                    or asset.resource_type != "image"
                ):
                    raise ValueError("Choose a public image asset.")
            if resource == "users":
                if form.password.data:
                    record.set_password(form.password.data)
                if record_id and db.inspect(record).attrs.role_id.history.has_changes():
                    record.session_version += 1
                    audit("role change", "User", record.id)
            if resource == "roles":
                record.permissions = list(
                    db.session.scalars(
                        db.select(m.Permission).where(
                            m.Permission.id.in_(form.permissions.data)
                        )
                    )
                )
            if resource == "blog":
                record.tags = list(
                    db.session.scalars(
                        db.select(m.BlogTag).where(m.BlogTag.id.in_(form.tags.data))
                    )
                )
            db.session.add(record)
            db.session.flush()
            audit("update" if record_id else "create", model.__name__, record.id)
            db.session.commit()
            cache.clear()
            flash("Changes saved.", "success")
            return redirect(url_for("admin.listing", resource=resource))
        except (ValueError, IntegrityError) as exc:
            db.session.rollback()
            flash(
                str(exc)
                if isinstance(exc, ValueError)
                else "This record conflicts with an existing record or relationship.",
                "error",
            )
    return render_template(
        "admin/edit.html",
        title=("Edit " if record_id else "Add ") + resource.rstrip("s"),
        form=form,
        resource=resource,
    )


@admin_bp.post("/manage/<resource>/<int:record_id>/delete")
def delete(resource, record_id):
    model, _, _ = allowed_resource(resource, "delete")
    if resource in {"donations", "receipts", "audit", "permissions", "registrations"}:
        abort(405)
    if resource in {"roles", "users"} and current_user.role.name != "SUPER_ADMIN":
        abort(403)
    record = db.get_or_404(model, record_id)
    if resource == "users" and (
        record.id == current_user.id or record.role.name == "SUPER_ADMIN"
    ):
        abort(403)
    if resource == "roles" and record.name == "SUPER_ADMIN":
        abort(403)
    try:
        if resource == "media":
            # Block deletion before the external asset is removed.
            referenced = any(
                db.session.scalar(
                    db.select(func.count(c.id)).where(getattr(c, field) == record.id)
                )
                for c, field in [
                    (m.Document, "media_id"),
                    (m.Gallery, "media_id"),
                    (m.ProjectImage, "media_id"),
                    (m.VolunteerApplication, "resume_id"),
                ]
            )
            referenced = referenced or any(
                db.session.scalar(
                    db.select(func.count(c.id)).where(
                        c.cover_image == record.secure_url
                    )
                )
                for c in [
                    m.Page,
                    m.Project,
                    m.Artisan,
                    m.Event,
                    m.BlogPost,
                    m.Gallery,
                    m.ImpactStory,
                ]
            )
            referenced = referenced or db.session.scalar(
                db.select(func.count(m.OrganizationSetting.id)).where(
                    m.OrganizationSetting.key.in_(["logo", "favicon", "hero_image"]),
                    m.OrganizationSetting.value == record.secure_url,
                )
            )
            if referenced:
                raise ValueError(
                    "This media is in use. Remove its references before deleting it."
                )
            MediaService().delete_asset(record)
        else:
            db.session.delete(record)
        audit("delete", model.__name__, record_id)
        db.session.commit()
        cache.clear()
        flash("Record deleted.", "success")
    except (IntegrityError, ValueError):
        db.session.rollback()
        flash("This record is in use and cannot be deleted.", "error")
    return redirect(url_for("admin.listing", resource=resource))


@admin_bp.post("/manage/<resource>/<int:record_id>/status")
def status(resource, record_id):
    model, _, _ = allowed_resource(resource, "edit")
    transitions = {
        "volunteers": {"Pending", "Approved", "Rejected"},
        "contacts": {"New", "Replied", "Archived"},
    }
    target = request.form.get("status")
    if target not in transitions.get(resource, set()):
        abort(400)
    record = db.get_or_404(model, record_id)
    changed = record.status != target
    record.status = target
    if changed and resource == "volunteers" and target == "Approved":
        queue_email(
            record.email,
            "Your volunteer application is approved",
            "approved",
            name=record.name,
        )
    audit("status " + target, model.__name__, record_id)
    db.session.commit()
    flash("Status updated.", "success")
    return redirect(url_for("admin.listing", resource=resource))


@admin_bp.get("/manage/<resource>/export")
def export(resource):
    model, _, _ = allowed_resource(resource, "export")
    columns = PRIVATE_COLUMNS.get(resource)
    if resource not in {
        "donations",
        "volunteers",
        "registrations",
        "contacts",
        "subscribers",
    }:
        abort(404)
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(columns)
    for record in db.session.scalars(db.select(model).order_by(model.id)):
        writer.writerow([csv_safe(getattr(record, c)) for c in columns])
    audit("export", model.__name__)
    db.session.commit()
    return Response(
        "\ufeff" + stream.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={resource}.csv"},
    )


@admin_bp.post("/donations/<int:record_id>/refund")
@permission_required("donation.refund")
def refund(record_id):
    donation = db.get_or_404(m.Donation, record_id)
    try:
        PaymentService().refund(donation)
        audit("refund requested", "Donation", record_id)
        db.session.commit()
        flash(
            "Refund request sent to the gateway. Status updates after processing.",
            "success",
        )
    except PaymentError as exc:
        db.session.rollback()
        flash(str(exc), "error")
    return redirect(url_for("admin.listing", resource="donations"))


@admin_bp.route("/media/upload", methods=["GET", "POST"])
@permission_required("media.upload")
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        try:
            if not file or not file.filename:
                raise ValueError("Choose a file.")
            kind = request.form.get("kind", "image")
            method = {
                "image": "upload_image",
                "video": "upload_video",
                "raw": "upload_document",
            }.get(kind)
            if not method:
                raise ValueError("Invalid media type.")
            private = request.form.get("visibility", "private") != "public"
            asset = getattr(MediaService(), method)(
                file, request.form.get("folder", "gallery"), private
            )
            audit("upload", "MediaAsset", asset.id)
            db.session.commit()
            flash("Media uploaded.", "success")
            return redirect(url_for("admin.listing", resource="media"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
        except Exception:
            db.session.rollback()
            current_app.logger.warning("Media provider upload failed")
            flash("The upload provider is unavailable. Please retry.", "error")
    return render_template(
        "admin/upload.html", title="Upload media", configured=MediaService.configured()
    )


@admin_bp.route("/media/<int:record_id>/replace", methods=["GET", "POST"])
@permission_required("media.upload")
def replace_media(record_id):
    if not current_user.can("media.edit"):
        abort(403)
    asset = db.get_or_404(m.MediaAsset, record_id)
    if request.method == "POST":
        try:
            file = request.files.get("file")
            if not file or not file.filename:
                raise ValueError("Choose a replacement file.")
            MediaService().replace_asset(asset, file)
            audit("replace media", "MediaAsset", asset.id)
            db.session.commit()
            flash("Media replaced.", "success")
            return redirect(url_for("admin.listing", resource="media"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
    return render_template(
        "admin/upload.html",
        title="Replace " + asset.title,
        configured=MediaService.configured(),
        replacing=True,
    )


@admin_bp.get("/media/<int:record_id>/download")
def media_download(record_id):
    asset = db.get_or_404(m.MediaAsset, record_id)
    if not current_user.can("media.view"):
        # Volunteer managers may access only resumes linked to volunteer applications.
        if not current_user.can("volunteer.view") or not db.session.scalar(
            db.select(m.VolunteerApplication).where(
                m.VolunteerApplication.resume_id == asset.id
            )
        ):
            abort(403)
    return redirect(
        MediaService.private_url(asset)
        if asset.visibility == "private"
        else asset.secure_url
    )


EDITOR_GROUPS = {
    "branding": ("Branding & homepage", ["logo", "favicon", "hero_image", "hero_image_alt", "hero_title", "hero_subtitle", "who_heading", "who_text", "footer_text"]),
    "leadership": ("Founder & leadership", ["founder_name", "founder_role", "founder_bio", "founder_image"]),
    "icps": ("ICPS feature", ["icps_intro", "icps_image"]),
    "recognition": ("Recognition — recipient is the founder", [f"{level}_award_{field}" for level in ("national", "state") for field in ("name", "year", "authority", "document_id", "verified")]),
}


@admin_bp.get("/content-studio")
@permission_required("admin.view")
def content_studio():
    pages = {p.slug: p for p in db.session.scalars(db.select(m.Page).where(m.Page.slug.in_(["icps", "about", "source-review-client-links"])))}
    return render_template("admin/content_studio.html", title="Website studio", pages=pages, groups=EDITOR_GROUPS)


@admin_bp.route("/website/<group>", methods=["GET", "POST"])
@permission_required("settings.manage")
def website_editor(group):
    if group not in EDITOR_GROUPS:
        abort(404)
    title, keys = EDITOR_GROUPS[group]
    return settings_screen(keys, title)


SETUP_GROUPS = [
    (
        "Organization information",
        ["organization_name", "location", "established", "recognition", "registration", "fcra", "80g", "12a", "csr"],
    ),
    ("Logo & branding", ["logo", "favicon", "hero_image"]),
    ("Contact information", ["phone", "mobile", "email", "address", "maps_url", "working_hours"]),
    ("Social media", ["whatsapp"]),
    ("Cloudinary", []),
    ("Email", []),
    ("Donation gateway", []),
    ("SEO", ["seo_description"]),
    (
        "Homepage content",
        ["hero_title", "hero_subtitle", "who_heading", "who_text", "footer_text"],
    ),
]


@admin_bp.route("/setup/<int:step>", methods=["GET", "POST"])
@permission_required("settings.manage")
def setup(step):
    if step < 1 or step > len(SETUP_GROUPS):
        abort(404)
    title, keys = SETUP_GROUPS[step - 1]
    return settings_screen(keys, title, step)


@admin_bp.route("/settings", methods=["GET", "POST"])
@permission_required("settings.manage")
def configure():
    return settings_screen(list(DEFAULTS), "Organization settings")


def settings_screen(keys, title, step=None):
    values = settings()
    attrs = {
        key: TextAreaField(
            key.replace("_", " ").title(), validators=[Optional(), Length(max=5000)]
        )
        for key in keys
        if key != "setup_complete"
    }
    attrs["submit"] = SubmitField("Save & continue" if step else "Save settings")
    form = type("SettingsForm", (FlaskForm,), attrs)(data=values)
    if form.validate_on_submit():
        try:
            for key in keys:
                if key == "setup_complete":
                    continue
                value = getattr(form, key).data or ""
                if key in {
                    "logo",
                    "favicon",
                    "hero_image",
                    "founder_image",
                    "icps_image",
                    "maps_url",
                } and not safe_url(value, media=key != "maps_url"):
                    raise ValueError("Use approved HTTPS media URLs.")
                if (
                    key == "whatsapp"
                    and value
                    and (not value.isdigit() or not 7 <= len(value) <= 15)
                ):
                    raise ValueError(
                        "WhatsApp must contain 7–15 digits, including country code."
                    )
                if key.endswith("_award_verified") and value not in {"true", "false"}:
                    raise ValueError("Award verification must be true or false.")
                if key.endswith("_award_year") and value and (not value.isdigit() or not 1900 <= int(value) <= 2100):
                    raise ValueError("Award year must be a four-digit year between 1900 and 2100.")
                if key.endswith("_award_document_id") and value:
                    document = db.session.get(m.Document, int(value)) if value.isdigit() else None
                    if not document or not document.media or document.visibility != "public" or document.media.visibility != "public" or document.media.format != "pdf":
                        raise ValueError("Select the ID of a public PDF document with a public media asset.")
                if key == "maintenance" and value not in {"true", "false"}:
                    raise ValueError("Maintenance must be true or false.")
                record = db.session.scalar(
                    db.select(m.OrganizationSetting).where(
                        m.OrganizationSetting.key == key
                    )
                )
                if not record:
                    record = m.OrganizationSetting(key=key)
                    db.session.add(record)
                record.value = value
            if any(key.endswith("_award_verified") for key in keys):
                from app.services.design_brief import recognition_cards
                pending = settings()
                for award in recognition_cards(pending):
                    if pending.get(award["level"].lower() + "_award_verified") == "true" and not award["ready"]:
                        raise ValueError("Verification requires the exact award name, year, authority and a public PDF certificate.")
            if step == len(SETUP_GROUPS):
                record = db.session.scalar(
                    db.select(m.OrganizationSetting).where(
                        m.OrganizationSetting.key == "setup_complete"
                    )
                )
                if not record:
                    record = m.OrganizationSetting(key="setup_complete")
                    db.session.add(record)
                record.value = "true"
            audit("settings update", "OrganizationSetting")
            db.session.commit()
            cache.clear()
            flash("Settings saved.", "success")
            return redirect(
                url_for("admin.setup", step=step + 1)
                if step and step < len(SETUP_GROUPS)
                else url_for("admin.dashboard")
            )
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
    return render_template(
        "admin/settings.html",
        title=title,
        form=form,
        step=step,
        total_steps=len(SETUP_GROUPS),
    )


@admin_bp.route("/media/remote", methods=["GET", "POST"])
@permission_required("media.upload")
def remote_media():
    from wtforms import SelectField
    from wtforms.validators import DataRequired

    class RemoteForm(FlaskForm):
        title = StringField("Title", validators=[DataRequired(), Length(max=180)])
        url = StringField(
            "HTTPS media or YouTube / Vimeo URL",
            validators=[DataRequired(), Length(max=1000)],
        )
        kind = SelectField(
            "Media type", choices=[("image", "Image"), ("video", "Video")]
        )
        alt_text = StringField("Alt text", validators=[Optional(), Length(max=250)])
        submit = SubmitField("Add public media")

    form = RemoteForm()
    if form.validate_on_submit():
        from urllib.parse import urlsplit

        value = form.url.data.strip()
        host = urlsplit(value).hostname
        video_hosts = {
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
            "vimeo.com",
            "www.vimeo.com",
        }
        valid = safe_url(value, media=True)
        if form.kind.data == "video" and host in video_hosts:
            valid = safe_url(value) and bool(
                current_app.jinja_env.filters["video_embed"](value)
            )
        if not valid:
            flash(
                "Use an approved media provider, YouTube video, or Vimeo video URL.",
                "error",
            )
        else:
            asset = m.MediaAsset(
                title=form.title.data,
                secure_url=value,
                resource_type=form.kind.data,
                visibility="public",
                alt_text=form.alt_text.data,
                folder="videos" if form.kind.data == "video" else "gallery",
            )
            db.session.add(asset)
            db.session.flush()
            audit("add remote URL", "MediaAsset", asset.id)
            db.session.commit()
            flash(
                "Public media added. Confirm you have permission to use it.", "success"
            )
            return redirect(url_for("admin.listing", resource="media"))
    return render_template(
        "admin/edit.html", title="Add remote media", form=form, resource="media"
    )


@admin_bp.get("/donors")
@permission_required("donation.view")
def donors():
    query = (
        db.select(
            m.Donation.email,
            func.count(m.Donation.id).label("count"),
            func.sum(m.Donation.amount).label("total"),
        )
        .where(m.Donation.status == "Paid")
        .group_by(m.Donation.email)
    )
    q = request.args.get("q", "").strip()[:100]
    if q:
        query = query.where(m.Donation.email.ilike(f"%{q}%"))
    records = db.session.execute(
        query.order_by(func.sum(m.Donation.amount).desc()).limit(500)
    ).all()
    return render_template("admin/donors.html", title="Donors", records=records, q=q)
