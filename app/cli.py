"""Operational CLI without a public bootstrap endpoint."""

import click
from flask import current_app
from app.extensions import db
from app import models as m
from app.admin.registry import REGISTRY
from app.services.content import DEFAULTS

ROLES = [
    "SUPER_ADMIN",
    "ADMIN",
    "EDITOR",
    "PROJECT_MANAGER",
    "VOLUNTEER_MANAGER",
    "FINANCE_MANAGER",
    "MEDIA_MANAGER",
    "VIEWER",
]


def seed_roles():
    prefixes = {spec[1] for spec in REGISTRY.values()}
    permissions = {
        f"{prefix}.{action}"
        for prefix in prefixes
        for action in ["view", "create", "edit", "delete", "publish", "export"]
    }
    permissions |= {"admin.view", "settings.manage", "media.upload", "donation.refund"}
    for name in sorted(permissions):
        if not db.session.scalar(
            db.select(m.Permission).where(m.Permission.name == name)
        ):
            db.session.add(m.Permission(name=name))
    db.session.flush()
    all_permissions = db.session.scalars(db.select(m.Permission)).all()
    groups = {
        "EDITOR": {"page", "blog", "impact", "artisan"},
        "PROJECT_MANAGER": {"project", "event"},
        "VOLUNTEER_MANAGER": {"volunteer", "event", "contact"},
        "FINANCE_MANAGER": {"donation"},
        "MEDIA_MANAGER": {"media", "document"},
        "VIEWER": set(),
    }
    for name in ROLES:
        role = db.session.scalar(db.select(m.Role).where(m.Role.name == name))
        if role:
            continue  # Never overwrite administrator-customized grants.
        role = m.Role(name=name)
        db.session.add(role)
        if name == "SUPER_ADMIN":
            role.permissions = all_permissions
        elif name == "ADMIN":
            role.permissions = [
                p for p in all_permissions if not p.name.startswith(("role.", "user."))
            ]
        elif name != "VIEWER":
            role.permissions = [
                p
                for p in all_permissions
                if p.name == "admin.view" or p.name.split(".")[0] in groups[name]
            ]
    db.session.flush()


PAGE_TITLES = {
    "awareness": "Awareness",
    "empowerment": "Empowerment",
    "about": "Who we are",
    "mission": "Our mission",
    "vision": "Our vision",
    "education": "Education",
    "women-empowerment": "Women empowerment",
    "skill-development": "Skill development",
    "livelihood-development": "Livelihood development",
    "handicrafts": "Handicrafts",
    "handlooms": "Handlooms",
    "community-development": "Community development",
    "associations": "Government & institutional associations",
    "csr-partners": "CSR partnerships",
    "privacy": "Privacy policy",
    "terms": "Terms",
    "cookie-policy": "Cookie policy",
}


def seed_content(demo=True):
    seed_roles()
    for key, value in DEFAULTS.items():
        if not db.session.scalar(
            db.select(m.OrganizationSetting).where(m.OrganizationSetting.key == key)
        ):
            db.session.add(m.OrganizationSetting(key=key, value=value))
    for slug, title in PAGE_TITLES.items():
        if not db.session.scalar(db.select(m.Page).where(m.Page.slug == slug)):
            description = "<p>Information will be updated by the organization.</p>"
            if slug == "about":
                description = "<p>Gyanpath Shiksha Evam Samaj Kalyan Samiti is an NGO / social welfare organization in Bhopal, Madhya Pradesh, India. Its areas of work include education, social welfare, community development, women empowerment, skill and livelihood development, and traditional crafts.</p><p>Official history, registrations and leadership information will be updated by the organization.</p>"
            if slug == "privacy":
                description = "<p>Policy draft — organization review required before public launch.</p><p>This platform stores the contact, volunteer, event and donation details you submit to process your request. Card details are handled by the payment gateway and are not stored here. Contact the organization to request correction or deletion. The organization must publish its privacy contact, retention periods and legal basis before collecting live submissions.</p>"
            if slug == "terms":
                description = "<p>Policy draft — organization review required before public launch.</p><p>Online donations are available only when enabled by the organization. A receipt confirms a recorded payment; it does not claim tax deductibility. The organization must supply its refund policy, eligibility terms and contact details before enabling live payments.</p>"
            if slug == "cookie-policy":
                description = "<p>This website uses essential session cookies for sign-in and form security. Theme and motion preferences are stored locally. Optional analytics require consent and organization configuration.</p>"
            db.session.add(
                m.Page(title=title, slug=slug, description=description, published=True)
            )
    for position, title in enumerate(
        ["Beneficiaries", "Projects", "Training programs", "Artisans supported"]
    ):
        if not db.session.scalar(
            db.select(m.ImpactStatistic).where(m.ImpactStatistic.title == title)
        ):
            db.session.add(
                m.ImpactStatistic(
                    title=title, value=0, verified=False, position=position
                )
            )
    from app.services.client_brief import apply_client_brief

    apply_client_brief()
    from app.services.design_brief import apply_design_brief
    apply_design_brief()
    if not demo:
        db.session.commit()
        return
    if current_app.config["PRODUCTION"]:
        raise click.ClickException(
            "Demo seeding is disabled in production. Use flask init-content and flask create-admin."
        )
    for account, role_name in [
        ("ADMIN", "SUPER_ADMIN"),
        ("STAFF", "EDITOR"),
        ("USER", "VIEWER"),
    ]:
        email = current_app.config[f"DEMO_{account}_EMAIL"]
        password = current_app.config[f"DEMO_{account}_PASSWORD"]
        if not email or len(password) < 12:
            raise click.ClickException(
                f"Set DEMO_{account}_EMAIL and DEMO_{account}_PASSWORD (12+ characters) in .env first."
            )
        email = email.lower().strip()
        if not db.session.scalar(db.select(m.User).where(m.User.email == email)):
            role = db.session.scalar(db.select(m.Role).where(m.Role.name == role_name))
            user = m.User(
                name=f"Demo {account.title()}", email=email, role=role, is_demo=True
            )
            user.set_password(password)
            db.session.add(user)
    samples = [
        (
            m.Project,
            "Community Skill Development Initiative",
            "community-skills",
            dict(status="Ongoing", location="Demo location — Bhopal", featured=True),
        ),
        (
            m.Project,
            "Learning Together",
            "learning-together",
            dict(status="Upcoming", featured=True),
        ),
        (
            m.Project,
            "Threads of Opportunity",
            "threads-of-opportunity",
            dict(status="Upcoming", featured=True),
        ),
        (
            m.Artisan,
            "Meet a craft practitioner",
            "demo-craft-practitioner",
            dict(
                skill="Demo weaving",
                craft="Handloom",
                location="Demo location — Bhopal",
            ),
        ),
        (
            m.Event,
            "Community craft exchange",
            "community-craft-exchange",
            dict(status="Upcoming", registration_enabled=True, registration_limit=30),
        ),
        (
            m.BlogPost,
            "Why preserving craft matters",
            "preserving-craft",
            dict(author="Demo editorial team"),
        ),
        (
            m.Gallery,
            "The texture of tradition",
            "texture-of-tradition",
            dict(category="Handloom"),
        ),
        (
            m.ImpactStory,
            "Learning, skills and shared possibility",
            "shared-possibility",
            dict(date_label="Date to be updated"),
        ),
    ]
    for model, title, slug, extra in samples:
        if not db.session.scalar(db.select(model).where(model.slug == slug)):
            db.session.add(
                model(
                    title=title,
                    slug=slug,
                    short_description="DEMO CONTENT — Replace with official information.",
                    description="<p>DEMO CONTENT — This record illustrates the platform. Replace it with verified organization information before publication.</p>",
                    cover_image="/static/images/craft.svg",
                    is_demo=True,
                    published=True,
                    **extra,
                )
            )
    if not db.session.scalar(db.select(m.FAQ.id).limit(1)):
        db.session.add(
            m.FAQ(
                question="How can I volunteer?",
                answer="Complete the volunteer application form. The organization will review your interests and availability.",
                published=True,
            )
        )
    db.session.commit()


def register_cli(app):
    @app.cli.command("apply-client-brief")
    def client_brief():
        """Apply supplied GSSKS facts and unpublish sample content (back up first)."""
        from app.services.client_brief import apply_client_brief
        seed_content(demo=False)
        apply_client_brief(overwrite=True)
        db.session.add(m.AuditLog(action="apply client brief", entity="OrganizationSetting"))
        db.session.commit()
        click.echo("Client facts applied. Demo content unpublished; custom projects and media preserved.")

    @app.cli.command("init-content")
    def init_content():
        """Create roles and configurable pages without sample users or claims."""
        seed_content(demo=False)
        click.echo("Organization content initialized.")

    @app.cli.command("create-admin")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(email, name, password):
        """Create an initial administrator from a private terminal."""
        from email_validator import validate_email, EmailNotValidError

        try:
            email = validate_email(email, check_deliverability=False).normalized.lower()
        except EmailNotValidError as exc:
            raise click.ClickException(str(exc))
        if len(password) < 12 or len(password) > 128:
            raise click.ClickException("Password must be 12–128 characters.")
        seed_roles()
        if db.session.scalar(db.select(m.User).where(m.User.email == email)):
            raise click.ClickException("This email already exists.")
        role = db.session.scalar(db.select(m.Role).where(m.Role.name == "SUPER_ADMIN"))
        user = m.User(email=email, name=name, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(
            m.AuditLog(
                user_id=user.id,
                action="create initial admin",
                entity="User",
                entity_id=str(user.id),
            )
        )
        db.session.commit()
        click.echo("Administrator created.")

    @app.cli.command("send-email")
    def send_email():
        """Drain the durable SMTP outbox; schedule every minute in production."""
        from app.services.email import drain_outbox

        click.echo(f"{drain_outbox()} messages sent.")

    @app.cli.command("check-config")
    def check_config():
        """Print configuration readiness, never secrets."""
        from app.services.media import MediaService
        from app.services.payments import PaymentService

        click.echo(
            f"Database: {'PostgreSQL' if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres') else 'SQLite'}"
        )
        click.echo(
            f"Production configuration valid: {not app.config['CONFIGURATION_REQUIRED']}"
        )
        click.echo(f"Cloudinary configured: {MediaService.configured()}")
        click.echo(f"SMTP configured: {bool(app.config['MAIL_SERVER'])}")
        click.echo(f"Donations enabled: {PaymentService.enabled()}")
