"""Apply client-supplied facts without fabricating missing organization content."""
from datetime import date
from app.extensions import db
from app import models as m
from app.services.content import DEFAULTS

PROJECT_SLUG = "gandhi-shilp-bazaar-2024"


def apply_client_brief(overwrite=False):
    """Seed known facts; an explicit CLI refresh updates existing official facts."""
    for key, value in DEFAULTS.items():
        record = db.session.scalar(db.select(m.OrganizationSetting).where(m.OrganizationSetting.key == key))
        if record is None:
            db.session.add(m.OrganizationSetting(key=key, value=value))
        elif overwrite and key not in {"logo", "favicon", "hero_image", "whatsapp", "maps_url", "working_hours", "fcra", "80g", "12a", "csr", "maintenance", "setup_complete"}:
            record.value = value
    project = db.session.scalar(db.select(m.Project).where(m.Project.slug == PROJECT_SLUG))
    if project is None:
        project = m.Project(slug=PROJECT_SLUG)
        db.session.add(project)
        project.title = "Gandhi Shilp Bazaar"
        project.short_description = "11–17 September 2024 · Urban Haat, Gauhar Mahal, Bhopal. An artisan exhibition documented in the organization’s client brief."
        project.description = "<p>Gandhi Shilp Bazaar took place from 11 to 17 September 2024 at Urban Haat, Gauhar Mahal, Bhopal.</p><p>The organization reports that the exhibition benefited 50 artisans and recorded sales of ₹14,95,577+.</p><p>Source: organization-supplied website brief. These figures relate to this exhibition only; they are not organization-wide totals. Photographs and supporting documents will be published after organization approval.</p>"
        project.location = "Urban Haat, Gauhar Mahal, Bhopal"
        project.start_date = date(2024, 9, 11)
        project.end_date = date(2024, 9, 17)
        project.status = "Completed"
        project.beneficiary_count = 50
        project.progress = 100
        project.outcomes = "<p>50 artisans benefited.</p><p>Reported exhibition sales: ₹14,95,577+.</p>"
        project.impact = "<p>Results are specific to Gandhi Shilp Bazaar, 11–17 September 2024. Sales are artisan exhibition sales, not NGO income or donations.</p>"
        project.featured = True
        project.published = True
        project.is_demo = False
    about = db.session.scalar(db.select(m.Page).where(m.Page.slug == "about"))
    if about and (overwrite or "Official history, registrations" in about.description):
        about.title = "About GSSKS"
        about.description = "<p>" + DEFAULTS["who_text"] + "</p><p>Registration No.: 1262/92.</p><p>The organization will provide its official mission, vision, objectives and leadership information before publication.</p>"
    if overwrite:
        for model in (m.Project, m.Artisan, m.Event, m.BlogPost, m.Gallery, m.ImpactStory):
            for record in db.session.scalars(db.select(model).where(model.is_demo.is_(True))):
                record.published = False
    db.session.flush()
