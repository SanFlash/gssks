import pytest
import os
from app import create_app
from app.extensions import db
from app.cli import seed_content


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SHOW_DEMO_CONTENT": True,
            "SQLALCHEMY_DATABASE_URI": os.getenv("TEST_DATABASE_URL", "sqlite://"),
            "SECRET_KEY": "test-secret-" * 4,
            "WTF_CSRF_ENABLED": False,
            "RATELIMIT_ENABLED": False,
            "PRODUCTION": False,
            "CONFIGURATION_REQUIRED": False,
            "DONATIONS_ENABLED": False,
            "MAIL_SERVER": "",
            "DEMO_ADMIN_EMAIL": "admin.demo@gyanpath.local",
            "DEMO_ADMIN_PASSWORD": "Gyanpath@Demo2026!",
            "DEMO_STAFF_EMAIL": "staff.demo@gyanpath.local",
            "DEMO_STAFF_PASSWORD": "Gyanpath@Demo2026!",
            "DEMO_USER_EMAIL": "user.demo@gyanpath.local",
            "DEMO_USER_PASSWORD": "Gyanpath@Demo2026!",
        }
    )
    with app.app_context():
        db.create_all()
        seed_content(demo=True)
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(client):
    result = client.post(
        "/login",
        data={"email": "admin.demo@gyanpath.local", "password": "Gyanpath@Demo2026!"},
    )
    assert result.status_code == 302
    return client
