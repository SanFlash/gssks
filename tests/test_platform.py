import hashlib
import hmac
import io
import json
import pytest
from werkzeug.datastructures import FileStorage
from app.extensions import db
from app import models as m
from app.services.media import MediaService
from app.services.payments import PaymentService, PaymentError
from app.services.applications import register_event, ApplicationError
from app.admin.registry import REGISTRY

PUBLIC = [
    "/",
    "/about",
    "/mission",
    "/vision",
    "/work",
    "/education",
    "/women-empowerment",
    "/skill-development",
    "/livelihood-development",
    "/handicrafts",
    "/handlooms",
    "/community-development",
    "/artisans",
    "/projects",
    "/projects/community-skills",
    "/impact",
    "/impact-stories",
    "/events",
    "/events/community-craft-exchange",
    "/gallery",
    "/videos",
    "/blog",
    "/blog/preserving-craft",
    "/reports",
    "/annual-reports",
    "/certificates",
    "/documents",
    "/associations",
    "/csr-partners",
    "/volunteer",
    "/volunteer/register",
    "/donate",
    "/contact",
    "/faq",
    "/privacy",
    "/terms",
    "/cookie-policy",
    "/login",
    "/admin/login",
    "/search?q=Community",
    "/sitemap.xml",
    "/robots.txt",
    "/health",
]


@pytest.mark.parametrize("path", PUBLIC)
def test_public_routes(client, path):
    response = client.get(path)
    assert response.status_code == 200, (path, response.data[:300])


@pytest.mark.parametrize("resource", list(REGISTRY))
def test_admin_lists(admin, resource):
    assert admin.get("/admin/manage/" + resource).status_code == 200


@pytest.mark.parametrize(
    "resource", [k for k, v in REGISTRY.items() if v[2] and k != "media"]
)
def test_admin_create_forms(admin, resource):
    assert admin.get("/admin/manage/" + resource + "/new").status_code == 200


def test_admin_dashboard(admin):
    assert admin.get("/admin").status_code == 200


def test_auth_and_roles(client):
    assert client.get("/admin").status_code == 302
    result = client.post(
        "/login", data={"email": "admin.demo@gyanpath.local", "password": "wrong"}
    )
    assert b"Sign-in failed" in result.data
    client.post(
        "/login",
        data={"email": "user.demo@gyanpath.local", "password": "Gyanpath@Demo2026!"},
    )
    assert client.get("/admin").status_code == 403


def test_editor_cannot_finance(client):
    client.post(
        "/login",
        data={"email": "staff.demo@gyanpath.local", "password": "Gyanpath@Demo2026!"},
    )
    assert client.get("/admin/manage/donations").status_code == 403
    assert client.get("/admin/manage/users/new").status_code == 403
    assert client.get("/admin/manage/blog/new").status_code == 200


def test_project_crud(admin):
    data = {
        "title": "Verified Project",
        "slug": "verified-project",
        "short_description": "Test description",
        "description": "<p>Safe</p><script>alert(1)</script>",
        "category_id": "0",
        "status": "Ongoing",
        "progress": "20",
        "beneficiary_count": "0",
        "target": "10",
        "published": "y",
    }
    assert admin.post("/admin/manage/projects/new", data=data).status_code == 302
    record = db.session.scalar(
        db.select(m.Project).where(m.Project.slug == "verified-project")
    )
    assert record and "<script>" not in record.description
    assert admin.get("/projects/verified-project").status_code == 200
    data["progress"] = "101"
    assert (
        admin.post(f"/admin/manage/projects/{record.id}/edit", data=data).status_code
        == 200
    )
    db.session.refresh(record)
    assert record.progress == 20
    assert admin.post(f"/admin/manage/projects/{record.id}/delete").status_code == 302
    assert admin.get("/projects/verified-project").status_code == 404


def test_contact_validation_and_storage(client):
    assert client.post("/api/contact", json={}).status_code == 422
    result = client.post(
        "/api/contact",
        json={
            "name": "Test User",
            "email": "person@example.org",
            "phone": "",
            "subject": "Partnership",
            "message": "I would like to discuss a partnership.",
            "consent": True,
        },
    )
    assert result.status_code == 201, result.json
    assert db.session.scalar(db.select(m.ContactMessage)).subject == "Partnership"
    assert db.session.scalar(db.select(m.EmailJob))


def test_volunteer_duplicate(client):
    data = {
        "name": "Test Person",
        "email": "person@example.org",
        "phone": "9876543210",
        "city": "Bhopal",
        "age": 25,
        "occupation": "Teacher",
        "skills": "Teaching",
        "availability": "Weekends",
        "areas_of_interest": "Teaching",
        "message": "",
        "consent": True,
    }
    assert client.post("/api/volunteers", json=data).status_code == 201
    assert client.post("/api/volunteers", json=data).status_code == 409
    data["consent"] = "false"
    assert client.post("/api/volunteers", json=data).status_code == 400


def test_event_capacity_and_duplicate(app):
    event = db.session.scalar(db.select(m.Event))
    event.registration_limit = 2
    db.session.commit()
    data = {"name": "Test", "email": "one@example.org", "phone": "", "consent": True}
    register_event(event, data)
    with pytest.raises(ApplicationError):
        register_event(event, data)
    db.session.refresh(event)
    assert event.registration_count == 1
    register_event(event, {**data, "email": "two@example.org"})
    with pytest.raises(ApplicationError):
        register_event(event, {**data, "email": "three@example.org"})
    assert db.session.scalar(db.select(db.func.count(m.EventRegistration.id))) == 2


def test_csrf(app, client):
    app.config["WTF_CSRF_ENABLED"] = True
    assert (
        client.post("/login", data={"email": "x", "password": "x"}).status_code == 400
    )
    assert client.post("/api/contact", json={}).status_code == 400


def test_private_documents(client):
    asset = m.MediaAsset(
        title="Private report",
        secure_url="https://res.cloudinary.com/demo/private.pdf",
        resource_type="raw",
        visibility="private",
    )
    db.session.add(asset)
    db.session.flush()
    doc = m.Document(title="Private", media=asset, visibility="private")
    db.session.add(doc)
    db.session.commit()
    assert client.get(f"/documents/{doc.id}/download").status_code == 403
    assert b"Private report" not in client.get("/documents").data


def test_upload_validation(app):
    for filename, mime, data, kind in [
        ("attack.exe", "application/octet-stream", b"MZbad", "image"),
        ("fake.png", "image/png", b"not image", "image"),
        ("active.pdf", "application/pdf", b"%PDF-1.4 /JavaScript test %%EOF", "raw"),
        (
            "big.pdf",
            "application/pdf",
            b"%PDF-" + b"x" * (6 * 1024 * 1024) + b"%%EOF",
            "raw",
        ),
    ]:
        with pytest.raises(ValueError):
            MediaService.validate(
                FileStorage(io.BytesIO(data), filename=filename, content_type=mime),
                kind,
            )


def test_oversized_upload(admin):
    assert (
        admin.post(
            "/admin/media/upload",
            data={"file": (io.BytesIO(b"x" * (26 * 1024 * 1024)), "large.mp4")},
            content_type="multipart/form-data",
        ).status_code
        == 413
    )


def test_payment_signature_capture_idempotency(app, monkeypatch):
    app.config.update(
        DONATIONS_ENABLED=True,
        RAZORPAY_KEY_ID="rzp_test_unit",
        RAZORPAY_KEY_SECRET="unit-secret",
    )
    d = m.Donation(
        name="Test Donor",
        email="donor@example.org",
        amount=10000,
        order_id="order_test",
        status="Pending",
    )
    db.session.add(d)
    db.session.commit()
    service = PaymentService()
    with pytest.raises(PaymentError):
        service.verify(d.token, "order_test", "pay_test", "invalid")
    assert d.status == "Pending"
    signature = hmac.new(
        b"unit-secret", b"order_test|pay_test", hashlib.sha256
    ).hexdigest()
    monkeypatch.setattr(
        PaymentService,
        "gateway",
        staticmethod(
            lambda *a, **k: {
                "order_id": "order_test",
                "amount": 10000,
                "currency": "INR",
                "status": "authorized",
            }
        ),
    )
    with pytest.raises(PaymentError):
        service.verify(d.token, "order_test", "pay_test", signature)
    assert d.status == "Pending"
    monkeypatch.setattr(
        PaymentService,
        "gateway",
        staticmethod(
            lambda *a, **k: {
                "order_id": "order_test",
                "amount": 10000,
                "currency": "INR",
                "status": "captured",
                "method": "upi",
            }
        ),
    )
    assert service.verify(d.token, "order_test", "pay_test", signature).status == "Paid"
    service.verify(d.token, "order_test", "pay_test", signature)
    assert db.session.scalar(db.select(db.func.count(m.DonationReceipt.id))) == 1


def test_no_fake_payment_success(client):
    assert client.get("/donation-success/madeup").status_code == 404
    assert (
        client.post("/api/donations/verify", json={"status": "Paid"}).status_code == 400
    )
    assert b"not enabled" in client.get("/donate").data


def test_webhook_signature(app, client):
    app.config["RAZORPAY_WEBHOOK_SECRET"] = "test"
    assert (
        client.post(
            "/api/donations/webhook",
            json={"event": "payment.captured"},
            headers={"X-Razorpay-Signature": "fake"},
        ).status_code
        == 400
    )


def test_password_cooldown(client):
    for _ in range(5):
        client.post(
            "/login", data={"email": "admin.demo@gyanpath.local", "password": "wrong"}
        )
    response = client.post(
        "/login",
        data={"email": "admin.demo@gyanpath.local", "password": "Gyanpath@Demo2026!"},
    )
    assert response.status_code == 200 and b"Sign-in failed" in response.data


def test_reset_token_single_use(app, client):
    from itsdangerous import URLSafeTimedSerializer

    user = db.session.scalar(
        db.select(m.User).where(m.User.email == "admin.demo@gyanpath.local")
    )
    token = URLSafeTimedSerializer(app.secret_key).dumps(
        {"id": user.id, "version": user.session_version}, salt="reset"
    )
    assert (
        client.post(
            "/reset-password/" + token,
            data={
                "password": "NewStrongPass2026!",
                "confirmation": "NewStrongPass2026!",
            },
        ).status_code
        == 302
    )
    assert client.get("/reset-password/" + token).status_code == 302
    assert user.check_password("NewStrongPass2026!")


def test_production_hides_demo(app, client):
    app.config["PRODUCTION"] = True
    app.config["DEMO_MODE"] = False
    assert b"admin.demo" not in client.get("/login").data
    assert client.get("/projects/community-skills").status_code == 404
    items = client.get("/api/projects").json["items"]
    assert all(not item["is_demo"] for item in items)
    assert any(item["slug"] == "gandhi-shilp-bazaar-2024" for item in items)
    assert (
        client.post(
            "/login",
            data={
                "email": "admin.demo@gyanpath.local",
                "password": "Gyanpath@Demo2026!",
            },
        ).status_code
        == 200
    )


def test_headers_and_errors(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors" in response.headers["Content-Security-Policy"]
    assert client.get("/api/missing").is_json


def test_csv_injection(admin):
    db.session.add(
        m.ContactMessage(
            name="=1+1", email="test@example.org", subject="Hi", message="Test message"
        )
    )
    db.session.commit()
    response = admin.get("/admin/manage/contacts/export")
    assert response.status_code == 200 and b"'=1+1" in response.data


def test_foreign_key_protection(app):
    from sqlalchemy.exc import IntegrityError

    db.session.add(m.ProjectImage(project_id=999, media_id=999))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_500_is_safe(app, client):
    @app.get("/test-boom")
    def boom():
        raise RuntimeError("private-secret-must-not-render")

    response = client.get("/test-boom")
    assert response.status_code == 500
    assert b"private-secret" not in response.data


def test_setup_and_settings(admin):
    for step in range(1, 10):
        assert admin.get(f"/admin/setup/{step}").status_code == 200
    assert (
        admin.post(
            "/admin/setup/1",
            data={"organization_name": "Updated organization", "location": "Bhopal"},
        ).status_code
        == 302
    )
    assert b"Updated organization" in admin.get("/").data


def test_permission_publish_independent(admin, client):
    role = db.session.scalar(db.select(m.Role).where(m.Role.name == "EDITOR"))
    role.permissions = [p for p in role.permissions if p.name != "blog.publish"]
    db.session.commit()
    client.post("/logout")
    client.post(
        "/login",
        data={"email": "staff.demo@gyanpath.local", "password": "Gyanpath@Demo2026!"},
    )
    result = client.post(
        "/admin/manage/blog/new",
        data={
            "title": "New blog",
            "slug": "new-blog",
            "published": "y",
            "category_id": "0",
        },
    )
    assert result.status_code == 403


def test_payment_amount_mismatch(app, monkeypatch):
    app.config.update(
        DONATIONS_ENABLED=True,
        RAZORPAY_KEY_ID="rzp_test_unit",
        RAZORPAY_KEY_SECRET="secret",
    )
    d = m.Donation(
        name="Test",
        email="test@example.org",
        amount=50000,
        order_id="order_mismatch",
        status="Pending",
    )
    db.session.add(d)
    db.session.commit()
    signature = hmac.new(
        b"secret", b"order_mismatch|pay_test", hashlib.sha256
    ).hexdigest()
    monkeypatch.setattr(
        PaymentService,
        "gateway",
        staticmethod(
            lambda *a, **k: {
                "order_id": "order_mismatch",
                "amount": 100,
                "currency": "INR",
                "status": "captured",
            }
        ),
    )
    with pytest.raises(PaymentError):
        PaymentService().verify(d.token, "order_mismatch", "pay_test", signature)
    assert d.status == "Pending"


def test_login_with_real_csrf(app, client):
    import re

    app.config["WTF_CSRF_ENABLED"] = True
    html = client.get("/login").text
    token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', html).group(1)
    response = client.post(
        "/login",
        data={
            "email": "admin.demo@gyanpath.local",
            "password": "Gyanpath@Demo2026!",
            "csrf_token": token,
        },
    )
    assert response.status_code == 302
    assert client.get("/admin").status_code == 200


def test_donor_summary_and_remote_forms(admin):
    assert admin.get("/admin/donors").status_code == 200
    assert admin.get("/admin/media/remote").status_code == 200
    response = admin.post(
        "/admin/media/remote",
        data={
            "title": "Unsafe",
            "url": "https://attacker.example/image.jpg",
            "kind": "image",
            "alt_text": "Test",
        },
    )
    assert response.status_code == 200
    assert b"approved media provider" in response.data


def test_form_real_csrf_json_and_browser(app, client):
    import re

    app.config["WTF_CSRF_ENABLED"] = True
    html = client.get("/contact").text
    token = re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', html).group(1)
    result = client.post(
        "/api/contact",
        json={
            "name": "API User",
            "email": "api@example.org",
            "phone": "",
            "subject": "Hello",
            "message": "A valid API message.",
            "consent": True,
        },
        headers={"X-CSRFToken": token},
    )
    assert result.status_code == 201, result.json
