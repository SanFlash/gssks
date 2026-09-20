"""Render Free startup: validate, migrate, seed official content, then serve."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    os.chdir(ROOT)
    os.environ.setdefault('FLASK_ENV', 'production')
    from app import create_app
    from flask_migrate import upgrade
    from app.cli import seed_content
    from app.services.deployment import bootstrap_admin
    app = create_app()
    if not app.config['PRODUCTION'] or app.config['CONFIGURATION_REQUIRED']:
        print('Render configuration incomplete: set FLASK_ENV=production, SECRET_KEY (32+ characters), and DATABASE_URL to your PostgreSQL connection URL.', flush=True)
        return 1
    try:
        with app.app_context():
            upgrade(directory=str(ROOT / 'migrations'))
            seed_content(demo=False)
            created = bootstrap_admin(os.getenv('INITIAL_ADMIN_EMAIL'), os.getenv('INITIAL_ADMIN_PASSWORD'))
            print('Database ready. Official content initialized. ' + ('Initial admin created.' if created else 'Existing admin preserved or initial admin not configured.'), flush=True)
    except ValueError as exc:
        print(str(exc), flush=True)
        return 1
    except Exception as exc:
        # Exception text may contain database credentials; log only its type.
        print(f'Database initialization failed ({type(exc).__name__}). Check DATABASE_URL, database availability, and migration logs.', flush=True)
        return 1
    port = os.getenv('PORT', '10000')
    if not port.isdigit():
        print('PORT must be numeric.', flush=True)
        return 1
    os.execv(sys.executable, [sys.executable, '-m', 'gunicorn', '--workers', '1', '--threads', '4', '--timeout', '120', '--bind', f'0.0.0.0:{port}', 'run:app'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
