"""Content queries enforce publication and privacy in one place."""

from datetime import date
from flask import current_app
from sqlalchemy import or_
from app.extensions import db, cache
from app.models import OrganizationSetting, SiteSetting, BlogPost

DEFAULTS = {
    "organization_name": "Gyan Path Shiksha Evam Samaj Kalyan Samiti",
    "location": "Bhopal, Madhya Pradesh, India",
    "hero_title": "Education.\nAwareness.\nEmpowerment.",
    "hero_subtitle": "A community-focused social-development organization in Bhopal, established in 1992 and recognised by the M.P. Government.",
    "who_heading": "Rooted in Bhopal. Since 1992.",
    "who_text": "Gyan Path Shiksha Evam Samaj Kalyan Samiti (GSSKS) was established in 1992 and is recognised by the M.P. Government. The organization works in education, awareness, empowerment, community development and artisan/livelihood-related programmes.",
    "footer_text": "Education, skills and craft. Pathways to a better future.",
    "email": "gyanpathngo.176@gmail.com",
    "phone": "0755-4278487",
    "mobile": "088893937454",
    "established": "1992",
    "recognition": "Recognised by the M.P. Government",
    "address": "Sunder Nagar, Chhola Road, Behind Dussehra Maidan, Block Fanda, Bhopal, Madhya Pradesh – 462001",
    "whatsapp": "",
    "logo": "",
    "favicon": "",
    "hero_image": "",
    "maps_url": "",
    "working_hours": "",
    "seo_description": "GSSKS, established in 1992 in Bhopal: education, awareness, empowerment, community development and artisan livelihoods.",
    "registration": "1262/92",
    "fcra": "",
    "80g": "",
    "12a": "",
    "csr": "",
    "maintenance": "false",
    "setup_complete": "false",
}


def settings():
    result = DEFAULTS.copy()
    for model in (OrganizationSetting, SiteSetting):
        result.update(
            {s.key: s.value for s in db.session.scalars(db.select(model)).all()}
        )
    return result


def published_query(model):
    query = db.select(model).where(model.published.is_(True))
    if hasattr(model, "is_demo") and (current_app.config["PRODUCTION"] or not current_app.config.get("SHOW_DEMO_CONTENT", False)):
        query = query.where(model.is_demo.is_(False))
    if model is BlogPost:
        query = query.where(
            or_(BlogPost.publish_date.is_(None), BlogPost.publish_date <= date.today())
        )
    return query


def content_list(model, limit=12):
    return db.session.scalars(
        published_query(model).order_by(model.created_at.desc()).limit(limit)
    ).all()
