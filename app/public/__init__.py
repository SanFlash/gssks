"""Public routes with publication filters and server-side validated forms."""

from datetime import date
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring
from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    redirect,
    url_for,
    flash,
    current_app,
    Response,
)
from flask_login import current_user
from sqlalchemy import or_
from app.extensions import db, limiter, cache
from app.models import (
    Project,
    Artisan,
    Event,
    BlogPost,
    Gallery,
    ImpactStory,
    ImpactStatistic,
    Page,
    PageSection,
    Document,
    MediaAsset,
    FAQ,
    Donation,
    NewsletterSubscriber,
)
from app.forms import (
    ContactForm,
    VolunteerForm,
    EventForm,
    NewsletterForm,
    DonationForm,
)
from app.services.content import published_query, content_list, settings
from app.services import applications
from app.services.media import MediaService
from app.services.payments import PaymentService
from app.services.design_brief import recognition_cards

public_bp = Blueprint("public", __name__)
COLLECTIONS = {
    "projects": Project,
    "artisans": Artisan,
    "events": Event,
    "blog": BlogPost,
    "gallery": Gallery,
    "impact-stories": ImpactStory,
}
FOCUS = [
    ("icps", "Child Protection", "ICPS and child-focused work."),
    ("education", "Education", "Education-related work and programmes."),
    ("awareness", "Awareness", "Information and community awareness."),
    ("empowerment", "Empowerment", "Empowerment-related activities."),
    ("community-development", "Community development", "Community-focused social development."),
    ("livelihood-development", "Artisan & livelihood development", "Artisan and livelihood-related programmes."),
]



@public_bp.get("/")
def home():
    return render_template(
        "public/home.html",
        title="GSSKS · Child Protection & Social Development",
        awards=recognition_cards(settings()),
        documents=public_documents(3),
        gallery=content_list(Gallery, 3),
        news=content_list(BlogPost, 3),
        events=content_list(Event, 3),
        projects=content_list(Project, 3),
        artisans=content_list(Artisan, 6),
        stories=content_list(ImpactStory, 3),
        focus=FOCUS,
        stats=db.session.scalars(
            db.select(ImpactStatistic).order_by(ImpactStatistic.position)
        ).all(),
    )


def public_documents(limit=30):
    return db.session.scalars(db.select(Document).join(MediaAsset).where(Document.visibility == "public", MediaAsset.visibility == "public").order_by(Document.created_at.desc()).limit(limit)).all()


@public_bp.get("/recognition")
def recognition():
    return render_template("public/recognition.html", title="Leadership & Recognition", awards=recognition_cards(settings()))


@public_bp.get("/icps")
def icps():
    record = db.session.scalar(published_query(Page).where(Page.slug == "icps"))
    if not record:
        abort(404)
    sections = db.session.scalars(db.select(PageSection).where(PageSection.page_id == record.id).order_by(PageSection.position)).all()
    photos = db.session.scalars(published_query(Gallery).where(Gallery.category == "ICPS").limit(12)).all()
    return render_template("public/icps.html", title=record.title, record=record, sections=sections, photos=photos)


@public_bp.get("/news-events")
def news_events():
    return render_template("public/news_events.html", title="News & Events", news=content_list(BlogPost, 30), events=content_list(Event, 30))


@public_bp.get("/get-involved")
def get_involved():
    return render_template("public/get_involved.html", title="Get Involved")


@public_bp.get("/work")
def work():
    return render_template("public/work.html", title="Our work", focus=FOCUS)


@public_bp.get("/impact")
def impact():
    return render_template(
        "public/impact.html",
        title="Impact, with transparency",
        projects=content_list(Project, 100),
        stats=db.session.scalars(
            db.select(ImpactStatistic).order_by(ImpactStatistic.position)
        ).all(),
        stories=content_list(ImpactStory, 100),
    )


@public_bp.get("/<section>")
def listing_or_page(section):
    if section in COLLECTIONS:
        model = COLLECTIONS[section]
        query = published_query(model)
        q = request.args.get("q", "").strip()[:100]
        category = request.args.get("category", "").strip()[:80]
        if q:
            query = query.where(model.title.ilike(f"%{q}%"))
        if section == "gallery" and category:
            query = query.where(Gallery.category == category)
        if section == "projects" and request.args.get("status") in {
            "Upcoming",
            "Ongoing",
            "Completed",
            "Archived",
        }:
            query = query.where(Project.status == request.args["status"])
        page = db.paginate(
            query.order_by(model.created_at.desc()),
            page=request.args.get("page", 1, type=int),
            per_page=12,
            max_per_page=12,
            error_out=False,
        )
        return render_template(
            "public/list.html",
            title=section.replace("-", " ").title(),
            section=section,
            records=page.items,
            pagination=page,
            q=q,
            gallery_categories=sorted({g.category for g in db.session.scalars(published_query(Gallery)).all() if g.category}) if section == "gallery" else [],
        )
    record = db.session.scalar(published_query(Page).where(Page.slug == section))
    if not record:
        abort(404)
    sections = db.session.scalars(
        db.select(PageSection)
        .where(PageSection.page_id == record.id)
        .order_by(PageSection.position)
    ).all()
    if section == "about":
        return render_template("public/about.html", title=record.title, record=record, sections=sections)
    if section in {"handicrafts", "handlooms"}:
        craft_query = published_query(Gallery).where(
            Gallery.category.in_(
                [
                    "Handicrafts",
                    "Textile",
                    "Handloom",
                    "Jute",
                    "Weaving",
                    "Traditional Craft",
                    "Decorative Craft",
                    "Other",
                ]
            )
        )
        category = request.args.get("category", "")[:80]
        if category:
            craft_query = craft_query.where(Gallery.category == category)
        return render_template(
            "public/crafts.html",
            title=record.title,
            record=record,
            records=db.session.scalars(craft_query.limit(60)).all(),
        )
    return render_template(
        "public/detail.html",
        title=record.seo_title or record.title,
        record=record,
        section="pages",
        sections=sections,
    )


@public_bp.get("/<section>/<slug>")
def detail(section, slug):
    model = COLLECTIONS.get(section)
    if not model:
        abort(404)
    record = db.session.scalar(published_query(model).where(model.slug == slug))
    if not record:
        abort(404)
    related = db.session.scalars(
        published_query(model).where(model.id != record.id).limit(3)
    ).all()
    gallery = []
    if section in {"artisans", "events"}:
        link = Gallery.artisan_id if section == "artisans" else Gallery.event_id
        gallery = db.session.scalars(
            published_query(Gallery).where(link == record.id)
        ).all()
    return render_template(
        "public/detail.html",
        title=record.seo_title or record.title,
        record=record,
        section=section,
        related=related,
        linked_gallery=gallery,
        event_form=EventForm() if section == "events" else None,
    )


@public_bp.route("/contact", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        applications.contact(form.data)
        flash("Thank you. Your enquiry has been received.", "success")
        return redirect(url_for("public.contact"))
    return render_template(
        "public/form.html",
        title="Let’s start a conversation.",
        intro="For questions, partnerships or an interest in our work, write to us.",
        form=form,
        contact=True,
    )


@public_bp.route("/volunteer", methods=["GET", "POST"])
@public_bp.route("/volunteer/register", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def volunteer():
    form = VolunteerForm()
    if form.validate_on_submit():
        try:
            applications.volunteer(form.data, form.resume.data)
            flash(
                "Your application has been received. Thank you for sharing your time and skills.",
                "success",
            )
            return redirect(url_for("public.volunteer"))
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "error")
    return render_template(
        "public/form.html",
        title="Your time. A shared future.",
        intro="Tell us how you would like to contribute. Applications are reviewed by the organization.",
        form=form,
    )


@public_bp.post("/events/<slug>/register")
@limiter.limit("5 per minute")
def register_event(slug):
    event = db.session.scalar(published_query(Event).where(Event.slug == slug))
    if not event:
        abort(404)
    form = EventForm()
    if form.validate_on_submit():
        try:
            applications.register_event(event, form.data)
            flash("Your event registration is confirmed.", "success")
            return redirect(url_for("public.detail", section="events", slug=slug))
        except ValueError as exc:
            flash(str(exc), "error")
    return render_template(
        "public/form.html",
        title="Register: " + event.title,
        form=form,
        intro="Please check your details before registering.",
    ), 400


@public_bp.post("/newsletter")
@limiter.limit("5 per minute")
def newsletter():
    form = NewsletterForm()
    if form.validate_on_submit():
        applications.subscribe(form.data)
        flash("Your subscription has been recorded.", "success")
        return redirect(url_for("public.home"))
    return render_template(
        "public/form.html",
        title="Stay connected",
        form=form,
        intro="Receive updates from the organization.",
    ), 400


@public_bp.route("/unsubscribe/<token>", methods=["GET", "POST"])
def unsubscribe(token):
    record = db.session.scalar(
        db.select(NewsletterSubscriber).where(
            NewsletterSubscriber.unsubscribe_token == token
        )
    )
    if not record:
        abort(404)
    if request.method == "POST":
        db.session.delete(record)
        db.session.commit()
        flash("You have been unsubscribed.", "success")
        return redirect(url_for("public.home"))
    return render_template("public/unsubscribe.html", title="Unsubscribe")


@public_bp.get("/donate")
def donate():
    return render_template(
        "public/donate.html",
        title="Support meaningful community development.",
        form=DonationForm(),
        payments_enabled=PaymentService.enabled(),
    )


@public_bp.get("/donation-success/<token>")
def donation_success(token):
    donation = db.session.scalar(
        db.select(Donation).where(Donation.token == token, Donation.status == "Paid")
    )
    if not donation:
        abort(404)
    return render_template(
        "public/success.html", title="Thank you for your support", donation=donation
    )


@public_bp.get("/donations/<token>/receipt")
def receipt(token):
    donation = db.session.scalar(
        db.select(Donation).where(
            Donation.token == token, Donation.status.in_(["Paid", "Refunded"])
        )
    )
    if not donation or not donation.receipt:
        abort(404)
    return render_template(
        "public/receipt.html", title="Donation receipt", donation=donation
    )


@public_bp.get("/reports")
@public_bp.get("/annual-reports")
@public_bp.get("/documents")
@public_bp.get("/certificates")
def documents():
    query = (
        db.select(Document)
        .join(MediaAsset)
        .where(Document.visibility == "public", MediaAsset.visibility == "public")
    )
    categories = {"/annual-reports": "Annual Reports", "/certificates": "Certificates"}
    if request.path in categories:
        query = query.where(Document.category == categories[request.path])
    return render_template(
        "public/documents.html",
        title=request.path[1:].replace("-", " ").title(),
        documents=db.session.scalars(query.order_by(Document.year.desc())).all(),
    )


@public_bp.get("/documents/<int:document_id>/download")
def download_document(document_id):
    record = db.get_or_404(Document, document_id)
    asset = record.media
    if record.visibility != "public" or asset.visibility != "public":
        if not current_user.is_authenticated or not current_user.can("document.view"):
            abort(403)
        return redirect(MediaService.private_url(asset))
    return redirect(asset.secure_url)


@public_bp.get("/videos")
def videos():
    assets = db.session.scalars(
        db.select(MediaAsset)
        .where(MediaAsset.resource_type == "video", MediaAsset.visibility == "public")
        .order_by(MediaAsset.created_at.desc())
    ).all()
    return render_template("public/videos.html", title="Videos", assets=assets)


@public_bp.get("/faq")
def faq():
    return render_template(
        "public/faq.html",
        title="Questions & answers",
        faqs=db.session.scalars(
            db.select(FAQ).where(FAQ.published.is_(True)).order_by(FAQ.position)
        ).all(),
    )


@public_bp.get("/search")
def search():
    q = request.args.get("q", "").strip()[:100]
    kind = request.args.get("type", "")
    results = []
    if q:
        for section, model in {**COLLECTIONS, "pages": Page}.items():
            if section in {"gallery", "impact-stories"} or (kind and section != kind):
                continue
            records = db.session.scalars(
                published_query(model)
                .where(
                    or_(model.title.ilike(f"%{q}%"), model.description.ilike(f"%{q}%"))
                )
                .limit(20)
            ).all()
            results.extend((section, record) for record in records)
    return render_template(
        "public/search.html", title="Find a path", q=q, results=results
    )


@public_bp.get("/sitemap.xml")
@cache.cached(timeout=120)
def sitemap():
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    urls = [
        "/",
        "/work",
        "/news-events",
        "/get-involved",
        "/impact",
        "/recognition",
        "/contact",
        "/volunteer",
        "/donate",
        "/faq",
        "/reports",
        "/videos",
        "/documents",
        "/annual-reports",
        "/certificates",
    ]
    for section, model in {**COLLECTIONS, "pages": Page}.items():
        if section != "pages":
            urls.append("/" + section)
        for record in db.session.scalars(published_query(model)).all():
            urls.append(
                "/" + record.slug if section == "pages" else f"/{section}/{record.slug}"
            )
    for path in urls:
        SubElement(SubElement(root, "url"), "loc").text = (
            current_app.config["SITE_URL"] + path
        )
    return Response(
        tostring(root, encoding="utf-8", xml_declaration=True),
        mimetype="application/xml",
    )


@public_bp.get("/robots.txt")
def robots():
    return Response(
        "User-agent: *\nDisallow: /admin\nDisallow: /api\nDisallow: /account\nDisallow: /donations/\nDisallow: /donation-success/\nSitemap: "
        + current_app.config["SITE_URL"]
        + "/sitemap.xml\n",
        mimetype="text/plain",
    )
