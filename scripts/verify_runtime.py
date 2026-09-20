"""Verify Python 3.13 and import every direct runtime dependency."""

import importlib
import importlib.metadata as metadata
import json
import sys

MODULES = {
    "Flask": "flask",
    "Flask-SQLAlchemy": "flask_sqlalchemy",
    "SQLAlchemy": "sqlalchemy",
    "Flask-Migrate": "flask_migrate",
    "Flask-Login": "flask_login",
    "Flask-WTF": "flask_wtf",
    "WTForms": "wtforms",
    "Flask-Caching": "flask_caching",
    "Flask-Limiter": "flask_limiter",
    "Flask-Mail": "flask_mail",
    "python-dotenv": "dotenv",
    "psycopg": "psycopg",
    "email-validator": "email_validator",
    "Werkzeug": "werkzeug",
    "cloudinary": "cloudinary",
    "Pillow": "PIL",
    "requests": "requests",
    "bleach": "bleach",
    "cryptography": "cryptography",
    "redis": "redis",
}
if sys.platform != "win32":
    MODULES["gunicorn"] = "gunicorn"
if sys.version_info[:2] != (3, 13):
    raise SystemExit("Expected Python 3.13.x; found " + sys.version)
result = {"python": sys.version.split()[0], "imports": {}}
for package, module in MODULES.items():
    importlib.import_module(module)
    result["imports"][package] = metadata.version(package)
print(json.dumps(result, indent=2))
