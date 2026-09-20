"""Build WTForms only from the reviewed CMS registry, never client model names."""

from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    TextAreaField,
    BooleanField,
    IntegerField,
    DateField,
    TimeField,
    SelectField,
    PasswordField,
    SelectMultipleField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    Optional,
    Length,
    NumberRange,
    Regexp,
    Email,
    ValidationError,
)
from sqlalchemy import Integer, Boolean, Text, Date, Time
from app.extensions import db
from app.models import Permission, BlogTag, MediaAsset
from app.utils.security import safe_url

CHOICES = {
    "Project.status": ["Upcoming", "Ongoing", "Completed", "Archived"],
    "Event.status": ["Upcoming", "Completed", "Cancelled", "Archived"],
    "Document.visibility": ["public", "private"],
    "Document.category": [
        "Annual Reports",
        "Certificates",
        "Government Documents",
        "Project Reports",
        "Policies",
        "Brochures",
        "Other Documents",
    ],
    "Gallery.category": [
        "ICPS",
        "Other Initiatives",
        "Projects",
        "Events",
        "Training",
        "Artisans",
        "Handicrafts",
        "Women Empowerment",
        "Education",
        "Community",
        "Textile",
        "Handloom",
        "Jute",
        "Weaving",
        "Traditional Craft",
        "Decorative Craft",
        "Other",
    ],
    "MediaAsset.folder": [
        "branding",
        "hero",
        "projects",
        "artisans",
        "events",
        "gallery",
        "videos",
        "documents",
        "blog",
    ],
}


def url_validator(form, field):
    if not safe_url(field.data, media=field.name == "cover_image"):
        raise ValidationError("Use an approved HTTPS URL or a local static image path.")


def build_form(model, fields, record=None):
    attrs = {}
    for name in fields:
        col = model.__table__.columns[name]
        label = name.replace("_id", "").replace("_", " ").title()
        optional = col.nullable or col.default is not None
        validators = [Optional() if optional else InputRequired()]
        if name in {"title", "slug", "name", "email", "question", "answer"}:
            validators = [DataRequired()]
        if col.foreign_keys:
            fk = next(iter(col.foreign_keys))
            table = fk.column.table
            rows = db.session.execute(db.select(table)).mappings().all()
            choices = [(0, "— None —")] if col.nullable else []
            choices += [
                (
                    r["id"],
                    str(
                        r.get("title") or r.get("name") or r.get("question") or r["id"]
                    ),
                )
                for r in rows
            ]
            attrs[name] = SelectField(
                label,
                choices=choices,
                coerce=int,
                validators=[InputRequired()] if not col.nullable else [],
            )
        elif isinstance(col.type, Boolean):
            attrs[name] = BooleanField(label)
        elif f"{model.__name__}.{name}" in CHOICES:
            attrs[name] = SelectField(
                label,
                choices=CHOICES[f"{model.__name__}.{name}"],
                validators=[DataRequired()],
            )
        elif isinstance(col.type, Integer):
            attrs[name] = IntegerField(
                label,
                validators=validators
                + [NumberRange(min=0, max=100 if name == "progress" else 1000000000)],
            )
        elif isinstance(col.type, Date):
            attrs[name] = DateField(label, validators=validators)
        elif isinstance(col.type, Time):
            attrs[name] = TimeField(label, validators=validators)
        elif isinstance(col.type, Text):
            attrs[name] = TextAreaField(
                label,
                validators=validators + [Length(max=50000)],
                render_kw={"class": "rich-source"},
            )
        else:
            validators += [Length(max=col.type.length or 500)]
            if name == "slug":
                validators += [
                    Regexp(
                        r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
                        message="Use lowercase words separated by hyphens.",
                    )
                ]
            if name in {"cover_image", "social_url", "url", "video"}:
                validators += [url_validator]
            if name == "email":
                validators += [Email(check_deliverability=False)]
            if name == "path":
                validators += [
                    Regexp(
                        r"^/(?!/)[a-zA-Z0-9/_-]*$",
                        message="Use a local path such as /projects.",
                    )
                ]
            attrs[name] = StringField(label, validators=validators)
    if model.__name__ == "User":
        attrs["password"] = PasswordField(
            "New password (leave blank to keep current)",
            validators=[
                Optional() if record else DataRequired(),
                Length(min=12, max=128),
            ],
        )
    if model.__name__ == "Role":
        attrs["permissions"] = SelectMultipleField(
            "Permissions",
            choices=[
                (p.id, p.name)
                for p in db.session.scalars(
                    db.select(Permission).order_by(Permission.name)
                )
            ],
            coerce=int,
        )
    if model.__name__ == "BlogPost":
        attrs["tags"] = SelectMultipleField(
            "Tags",
            choices=[
                (p.id, p.title)
                for p in db.session.scalars(db.select(BlogTag).order_by(BlogTag.title))
            ],
            coerce=int,
        )
    attrs["submit"] = SubmitField("Save changes")
    form = type("CMSForm", (FlaskForm,), attrs)(obj=record)
    return form
