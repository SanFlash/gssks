import pytest
from app.extensions import db
from app.models import User, Role
from app.cli import seed_roles
from app.services.deployment import bootstrap_admin


def test_first_admin_is_private_and_idempotent(app):
    db.session.query(User).delete()
    db.session.commit()
    seed_roles()
    with pytest.raises(ValueError):
        bootstrap_admin('invalid', 'long-enough-password')
    with pytest.raises(ValueError):
        bootstrap_admin('owner@example.org', 'short')
    assert bootstrap_admin('owner@example.org', 'PrivatePassword123!')
    assert not bootstrap_admin('other@example.org', 'DifferentPassword123!')
    user = db.session.scalar(db.select(User).where(User.email == 'owner@example.org'))
    assert user.check_password('PrivatePassword123!') and not user.is_demo
    assert user.role.name == 'SUPER_ADMIN'
    assert db.session.query(User).count() == 1


def test_bootstrap_is_optional(app):
    db.session.query(User).delete()
    db.session.commit()
    assert bootstrap_admin(None, None) is False


def test_render_rejects_missing_config(app, monkeypatch, capsys):
    from scripts import render_start
    import app as package
    monkeypatch.setattr(package, 'create_app', lambda: app)
    app.config['PRODUCTION'] = True
    app.config['CONFIGURATION_REQUIRED'] = True
    assert render_start.main() == 1
    assert 'DATABASE_URL' in capsys.readouterr().out


def test_render_initializes_before_gunicorn(app, monkeypatch):
    from scripts import render_start
    import app as package
    import flask_migrate
    import app.services.deployment as deployment
    calls = []
    monkeypatch.setattr(package, 'create_app', lambda: app)
    app.config.update(PRODUCTION=True, CONFIGURATION_REQUIRED=False)
    monkeypatch.setattr(flask_migrate, 'upgrade', lambda **kwargs: calls.append('migrate'))
    import importlib
    cli = importlib.import_module('app.cli')
    monkeypatch.setattr(cli, 'seed_content', lambda demo: calls.append(('seed', demo)))
    monkeypatch.setattr(deployment, 'bootstrap_admin', lambda *args: calls.append('admin'))
    monkeypatch.setattr(render_start.os, 'execv', lambda executable, args: calls.append(args))
    monkeypatch.setenv('PORT', '10000')
    assert render_start.main() == 0
    assert calls[:3] == ['migrate', ('seed', False), 'admin']
    assert '0.0.0.0:10000' in calls[3] and calls[3][-1] == 'run:app'
