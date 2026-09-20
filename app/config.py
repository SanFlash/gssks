"""Environment configuration. Optional services fail closed until configured."""

import os
import secrets
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def boolean(name, default=False):
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes"}


def configuration():
    production = os.getenv("FLASK_ENV") == "production"
    secret = os.getenv("SECRET_KEY", "")
    if not secret or secret == "change-me":
        secret_path = ROOT / "instance" / ".dev-secret"
        secret_path.parent.mkdir(exist_ok=True)
        if not production:
            if not secret_path.exists():
                secret_path.write_text(secrets.token_hex(32))
                secret_path.chmod(0o600)
            secret = secret_path.read_text().strip()
    url = (os.getenv("DATABASE_URL") or "sqlite:///gyanpath.db")
    if url.startswith(("postgres://", "postgresql://")):
        url = "postgresql+psycopg://" + url.split("://", 1)[1]
    config = dict(
        SECRET_KEY=secret or secrets.token_hex(32),
        PRODUCTION=production,
        TRUST_PROXY_HOPS=int(os.getenv("TRUST_PROXY_HOPS") or "0"),
        CONFIGURATION_REQUIRED=production
        and (len(secret) < 32 or not url.startswith("postgresql+psycopg://")),
        SQLALCHEMY_DATABASE_URI=url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=production,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=45),
        MAX_CONTENT_LENGTH=25 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=512 * 1024,
        WTF_CSRF_TIME_LIMIT=7200,
        CACHE_TYPE="SimpleCache",
        CACHE_DEFAULT_TIMEOUT=60,
        RATELIMIT_STORAGE_URI=(os.getenv("REDIS_URL") or "memory://"),
        MAIL_PORT=int(os.getenv("MAIL_PORT") or "587"),
        MAIL_USE_TLS=boolean("MAIL_USE_TLS", True),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", ""),
        SITE_URL=os.getenv("SITE_URL", "http://127.0.0.1:5000").rstrip("/"),
        DONATIONS_ENABLED=boolean("DONATIONS_ENABLED"),
        DEMO_MODE=not production,
        FIELD_ENCRYPTION_KEY=os.getenv("FIELD_ENCRYPTION_KEY", ""),
        REMOTE_MEDIA_HOSTS=os.getenv(
            "REMOTE_MEDIA_HOSTS",
            "images.unsplash.com,images.pexels.com,upload.wikimedia.org,res.cloudinary.com",
        ).split(","),
    )
    for key in [
        "CLOUDINARY_CLOUD_NAME",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
        "MAIL_SERVER",
        "MAIL_USERNAME",
        "MAIL_PASSWORD",
        "RAZORPAY_KEY_ID",
        "RAZORPAY_KEY_SECRET",
        "RAZORPAY_WEBHOOK_SECRET",
        "GA_MEASUREMENT_ID",
    ]:
        config[key] = os.getenv(key, "")
    for account in ["ADMIN", "STAFF", "USER"]:
        for field in ["EMAIL", "PASSWORD"]:
            config[f"DEMO_{account}_{field}"] = (
                os.getenv(f"DEMO_{account}_{field}", "") if not production else ""
            )
    return config
