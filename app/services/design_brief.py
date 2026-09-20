"""Client UI revision: conservative, repeatable content upgrade."""
from app.extensions import db
from app import models as m
from app.services.content import DEFAULTS


def apply_design_brief():
    previous = {
        "hero_title": "Education.\nAwareness.\nEmpowerment.",
        "hero_subtitle": "A community-focused social-development organization in Bhopal, established in 1992 and recognised by the M.P. Government.",
        "footer_text": "Education, skills and craft. Pathways to a better future.",
    }
    for key, value in DEFAULTS.items():
        row = db.session.scalar(db.select(m.OrganizationSetting).where(m.OrganizationSetting.key == key))
        if row is None:
            db.session.add(m.OrganizationSetting(key=key, value=value))
        elif key in previous and row.value == previous[key]:
            row.value = value
    page = db.session.scalar(db.select(m.Page).where(m.Page.slug == "icps"))
    if page is None:
        page = m.Page(title="Integrated Child Protection Services", slug="icps", short_description="ICPS is identified by GSSKS as its core area of work.", description="<p>Programme responsibilities and service details will be updated by the organization following approval.</p>", published=True)
        db.session.add(page)
        db.session.flush()
        for position, title in enumerate(["Our Role", "Children We Support", "Services & Interventions", "Our Approach", "Programme Locations", "Impact", "Documentation"]):
            db.session.add(m.PageSection(page_id=page.id, title=title, content="<p>Official information will be updated by the organization.</p>", position=position))
    source = db.session.scalar(db.select(m.Page).where(m.Page.slug == "source-review-client-links"))
    if source is None:
        db.session.add(m.Page(title="PRIVATE REVIEW — client source links", slug="source-review-client-links", published=False, description="<h2>Changes.pdf: editorial source review</h2><p>The final brief identifies I. S. Chauhan as Founder and Director. Earlier business-card material says President; the newer client correction is used. Award names, years and certificates are not supplied.</p><p><a href='https://www.scribd.com/document/1068052435/MP-Report-No-2-of-2026-English-06a61c242e0da69-34500633'>Scribd-hosted audit report</a>: references the organization in child-care/open-shelter context and contains adverse audit findings. Do not recast occupancy figures as verified impact or endorsements. Obtain the primary report and organization response before publication.</p><p><a href='https://handicrafts.nic.in/pdf/dc_hc_GIA1314.pdf'>Handicrafts source</a>: retrieval failed; no new claim or project imported. Request an official copy.</p><p>The exhibition report referenced by filename in Changes.pdf is not attached. Request the original report and approved photographs. Do not use generic child images.</p>"))
    db.session.flush()


def recognition_cards(values):
    """Publish a certificate only while its document and underlying asset are public."""
    cards = []
    for level in ("national", "state"):
        prefix = f"{level}_award_"
        raw = values.get(prefix + "document_id", "")
        document = db.session.get(m.Document, int(raw)) if raw.isdigit() else None
        public = bool(document and document.media and document.visibility == "public" and document.media.visibility == "public" and document.media.format == "pdf")
        ready = values.get(prefix + "verified") == "true" and public and all(values.get(prefix + f) for f in ("name", "year", "authority"))
        cards.append(dict(level=level.title(), ready=bool(ready), name=values.get(prefix+"name") if ready else "Details awaiting verification", year=values.get(prefix+"year") if ready else "", authority=values.get(prefix+"authority") if ready else "", document_id=document.id if ready else None))
    return cards
