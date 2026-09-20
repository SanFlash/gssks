from pathlib import Path
import pytest
from app.local_startup import prepare_local_environment, initialize_local_database
from app import create_app
from app.extensions import db
from app.models import User


def test_clean_local_startup_and_repeat(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    (tmp_path / '.env.example').write_text((root / '.env.example').read_text())
    for key in ['FLASK_ENV', 'SECRET_KEY', 'DATABASE_URL']:
        monkeypatch.delenv(key, raising=False)
    prepare_local_environment(tmp_path)
    original = (tmp_path / '.env').read_text()
    assert 'SECRET_KEY=change-me' not in original
    app = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + str(tmp_path / 'fresh.db'), 'PRODUCTION': False, 'CONFIGURATION_REQUIRED': False, 'RATELIMIT_ENABLED': False})
    initialize_local_database(app)
    with app.app_context():
        count = db.session.query(User).count()
    prepare_local_environment(tmp_path)
    initialize_local_database(app)
    assert (tmp_path / '.env').read_text() == original
    with app.app_context():
        assert db.session.query(User).count() == count == 3
    for path in ['/', '/login', '/projects', '/contact', '/get-involved']:
        assert app.test_client().get(path).status_code == 200


def test_production_is_not_bootstrapped(tmp_path, monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'production')
    with pytest.raises(RuntimeError, match='Production'):
        prepare_local_environment(tmp_path)
    assert not (tmp_path / '.env').exists()


def test_remote_database_is_not_bootstrapped(app):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg://example.invalid/db'
    with pytest.raises(RuntimeError, match='SQLite'):
        initialize_local_database(app)
