"""Shared authorization, URL policies and safe rich text."""

from functools import wraps
from urllib.parse import urlsplit
import bleach
from flask import abort, current_app, request, has_request_context
from flask_login import current_user, login_required
from app.extensions import db
from app.models import AuditLog


def permission_required(permission):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def audit(action, entity, entity_id=None):
    db.session.add(
        AuditLog(
            user_id=current_user.id
            if has_request_context() and current_user.is_authenticated
            else None,
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            ip=request.remote_addr if has_request_context() else None,
        )
    )


def rich_text(text):
    return bleach.clean(
        text or "",
        tags={
            "p",
            "br",
            "strong",
            "em",
            "ul",
            "ol",
            "li",
            "h2",
            "h3",
            "blockquote",
            "a",
        },
        attributes={"a": ["href", "title"]},
        protocols={"https", "mailto"},
        strip=True,
    )


def safe_url(value, media=False):
    if not value:
        return True
    parts = urlsplit(value)
    if value.startswith("/static/") and not parts.netloc and "\\" not in value:
        return True
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        return False
    if media:
        return parts.hostname in current_app.config["REMOTE_MEDIA_HOSTS"]
    return True


def csv_safe(value):
    value = "" if value is None else str(value)
    return (
        "'" + value
        if value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r"))
        else value
    )
