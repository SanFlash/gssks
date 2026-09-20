"""Explicit local launcher bootstrap; never invoked by production WSGI imports."""
import os
import secrets
from pathlib import Path
from dotenv import dotenv_values, load_dotenv
from flask_migrate import upgrade


def prepare_local_environment(root: Path) -> None:
    """Create missing local configuration without overwriting existing values."""
    env_path = root / '.env'
    existing = dotenv_values(env_path) if env_path.exists() else {}
    if os.environ.get('FLASK_ENV', existing.get('FLASK_ENV')) == 'production':
        raise RuntimeError('Production configuration detected. Use the production deployment instructions; local setup will not modify production data.')
    if not env_path.exists():
        content = (root / '.env.example').read_text(encoding='utf-8')
        content = content.replace('SECRET_KEY=change-me', 'SECRET_KEY=' + secrets.token_hex(32))
        with env_path.open('x', encoding='utf-8') as handle:
            handle.write(content)
        try:
            env_path.chmod(0o600)
        except OSError:
            pass
    load_dotenv(env_path, override=False)
    # Older local .env files may omit demo values. Defaults live in the example,
    # not in authentication code. Never replace an explicitly supplied value.
    for key, value in dotenv_values(root / '.env.example').items():
        if key.startswith('DEMO_') and value:
            os.environ.setdefault(key, value)


def initialize_local_database(app) -> None:
    """Use versioned migrations and idempotent seeds; refuse remote databases."""
    if app.config['PRODUCTION'] or not app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite:'):
        raise RuntimeError('Automatic local setup requires development mode and SQLite. Configure production separately.')
    from app.cli import seed_content
    with app.app_context():
        upgrade(directory=str(Path(app.root_path).parent / 'migrations'))
        seed_content(demo=True)
