"""JSON endpoints share forms, permissions and transactions with browser flows."""

import hashlib
import hmac
import json
from flask import Blueprint, request, jsonify, abort, current_app, url_for
from werkzeug.datastructures import MultiDict
from app.extensions import db, csrf, limiter
from app.models import Project, Event, Artisan, BlogPost, Page, Donation
from app.forms import ContactForm, VolunteerForm, DonationForm
from app.services.content import published_query
from app.services import applications
from app.services.payments import PaymentService, PaymentError

api_bp = Blueprint("api", __name__, url_prefix="/api")


def public_record(record):
    data = {
        k: getattr(record, k)
        for k in ["id", "title", "slug", "short_description", "cover_image", "is_demo"]
    }
    for k in ["location", "status", "progress", "beneficiary_count", "skill", "craft"]:
        if hasattr(record, k):
            data[k] = getattr(record, k)
    return data


@api_bp.get("/<resource>")
def listing(resource):
    model = {"projects": Project, "events": Event, "artisans": Artisan}.get(resource)
    if not model:
        abort(404)
    page = db.paginate(
        published_query(model).order_by(model.id.desc()),
        page=request.args.get("page", 1, type=int),
        per_page=20,
        max_per_page=20,
        error_out=False,
    )
    return jsonify(
        items=[public_record(r) for r in page.items],
        total=page.total,
        page=page.page,
        pages=page.pages,
    )


@api_bp.get("/projects/<slug>")
def project(slug):
    record = db.session.scalar(published_query(Project).where(Project.slug == slug))
    if not record:
        abort(404)
    data = public_record(record)
    data.update(
        description=record.description,
        objectives=record.objectives,
        activities=record.activities,
        outcomes=record.outcomes,
    )
    return jsonify(data)


def json_form(cls):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        abort(400, description="A JSON object is required.")
    # Reject structured objects and strings masquerading as checkbox booleans.
    for k, v in data.items():
        if (
            isinstance(v, (list, dict))
            or k in {"consent", "anonymous"}
            and not isinstance(v, bool)
        ):
            abort(400, description="Invalid field type.")
    return cls(
        formdata=MultiDict(
            {
                k: ("y" if v else "") if isinstance(v, bool) else v
                for k, v in data.items()
            }
        )
    )


@api_bp.post("/contact")
@limiter.limit("5 per minute")
def contact():
    form = json_form(ContactForm)
    if not form.validate():
        return jsonify(errors=form.errors), 422
    applications.contact(form.data)
    return jsonify(message="Enquiry received."), 201


@api_bp.post("/volunteers")
@limiter.limit("5 per minute")
def volunteer():
    form = json_form(VolunteerForm)
    if not form.validate():
        return jsonify(errors=form.errors), 422
    try:
        applications.volunteer(form.data)
    except ValueError as exc:
        return jsonify(error=str(exc)), 409
    return jsonify(message="Application received."), 201


@api_bp.post("/donations/create-order")
@limiter.limit("5 per minute")
def create_order():
    form = json_form(DonationForm)
    if not form.validate():
        return jsonify(errors=form.errors), 422
    try:
        donation = PaymentService().create_order(form.data)
        return jsonify(
            order_id=donation.order_id,
            token=donation.token,
            amount=donation.amount,
            currency=donation.currency,
            key_id=current_app.config["RAZORPAY_KEY_ID"],
        ), 201
    except PaymentError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 503


@api_bp.post("/donations/verify")
@limiter.limit("15 per minute")
def verify():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or any(
        not isinstance(data.get(k), str) or len(data[k]) > 200
        for k in ["token", "order_id", "payment_id", "signature"]
    ):
        abort(400)
    try:
        donation = PaymentService().verify(
            **{k: data[k] for k in ["token", "order_id", "payment_id", "signature"]}
        )
        return jsonify(
            status=donation.status,
            redirect=url_for("public.donation_success", token=donation.token),
        )
    except PaymentError as exc:
        db.session.rollback()
        return jsonify(error=str(exc)), 400


@api_bp.post("/donations/webhook")
@csrf.exempt
@limiter.limit("120 per minute")
def webhook():
    secret = current_app.config["RAZORPAY_WEBHOOK_SECRET"]
    if not secret:
        abort(503)
    body = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature", "")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        abort(400, description="Invalid webhook signature.")
    try:
        data = json.loads(body)
        event = data.get("event")
        if event in {"payment.captured", "order.paid"}:
            payment = data["payload"]["payment"]["entity"]
            PaymentService().reconcile(payment["order_id"], payment["id"])
        elif event == "payment.failed":
            entity = data["payload"]["payment"]["entity"]
            payment = PaymentService.gateway("GET", f"payments/{entity['id']}")
            donation = db.session.scalar(
                db.select(Donation)
                .where(Donation.order_id == payment.get("order_id"))
                .with_for_update()
            )
            if (
                donation
                and donation.status in {"Created", "Pending"}
                and payment.get("status") == "failed"
            ):
                donation.status = "Failed"
                db.session.commit()
        elif event == "refund.processed":
            refund = data["payload"]["refund"]["entity"]
            donation = db.session.scalar(
                db.select(Donation)
                .where(Donation.payment_id == refund["payment_id"])
                .with_for_update()
            )
            if donation:
                payment = PaymentService.gateway(
                    "GET", f"payments/{donation.payment_id}"
                )
                if (
                    payment.get("amount_refunded") == donation.amount
                    and payment.get("refund_status") == "full"
                ):
                    donation.status = "Refunded"
                    db.session.commit()
        return jsonify(received=True)
    except (ValueError, KeyError, TypeError):
        db.session.rollback()
        abort(400)


@api_bp.get("/search")
def search():
    q = request.args.get("q", "").strip()[:100]
    result = []
    if q:
        for name, model in {
            "projects": Project,
            "events": Event,
            "artisans": Artisan,
            "blog": BlogPost,
            "pages": Page,
        }.items():
            if request.args.get("type") and request.args["type"] != name:
                continue
            for record in db.session.scalars(
                published_query(model).where(model.title.ilike(f"%{q}%")).limit(20)
            ):
                result.append(dict(type=name, **public_record(record)))
    return jsonify(items=result)
