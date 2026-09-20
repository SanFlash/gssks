# Render Free setup — existing web service

GitHub source: https://github.com/SanFlash/gssks (main).
A SECRET_KEY alone cannot initialize the database. Use PostgreSQL on Render; its web filesystem cannot retain SQLite reliably.

## 1. Database

In Render, choose New > Postgres. Select Free and the same region as your web service. Wait for Available, then copy its Internal Database URL. Keep this URL private. If you already have a working PostgreSQL database, reuse it instead.

## 2. Existing web service settings

- Repository: SanFlash/gssks
- Branch: main
- Root directory: blank (repository root)
- Runtime: Python
- Instance type: Free
- Build command: `pip install -r requirements.txt`
- Start command: `python scripts/render_start.py`
- Pre-deploy command: empty
- Health check: `/health`

Changing render.yaml does not automatically reconfigure a manually created service. Apply these values in its dashboard settings.

## 3. Environment variables

| Variable | Value |
|---|---|
| PYTHON_VERSION | 3.13.15 |
| FLASK_ENV | production |
| SECRET_KEY | Your existing private random key, at least 32 characters |
| DATABASE_URL | Full Internal Database URL from your PostgreSQL database |
| SITE_URL | Actual web service URL, e.g. https://your-service.onrender.com |
| TRUST_PROXY_HOPS | 1 |
| DONATIONS_ENABLED | false |
| INITIAL_ADMIN_EMAIL | Email you will use to sign in |
| INITIAL_ADMIN_PASSWORD | Unique private password, 12–128 characters |

Do not add quotation marks around values. Never paste secrets into GitHub or chat. Remove an obsolete SQLite DATABASE_URL. Leave REDIS_URL unset unless a working Redis service exists; this free setup uses one worker. Leave Cloudinary, SMTP, Razorpay and analytics unset until configured. No .env upload is required: Render injects environment variables.

## 4. Deploy

Save settings/environment changes. Select Manual Deploy > Deploy latest commit. Logs should show migrations followed by `Database ready. Official content initialized.` and Gunicorn startup. The start command handles migrations and official-content seeding before serving requests; it does not seed public demo accounts.

Open `/`, `/projects`, `/contact`, and `/admin/login`. Sign in using INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD. After successful login, remove these two initialization variables and redeploy. The existing account remains in PostgreSQL; repeated startup never resets its password.

If an administrator already exists, initialization intentionally leaves it unchanged. Use that account; changing INITIAL_ADMIN_PASSWORD does not reset an existing password.

## Troubleshooting

- Old six-step configuration page: check that main's latest commit is deployed, FLASK_ENV is production, and the start command is updated.
- Configuration incomplete in logs: check secret length and PostgreSQL DATABASE_URL.
- Database initialization failed: database must be Available, unexpired, and reachable; use the complete correct connection URL. Migration logs identify schema failures without printing application secrets.
- 502/startup failure: inspect deploy logs and start command; do not use python run.py on Render, which is a localhost development launcher.
- Login cookie issue: use HTTPS and the correct SITE_URL; keep SECRET_KEY stable.

## Free-plan limits

Render free web services sleep after 15 minutes idle and lose local files on restart. Free PostgreSQL expires after 30 days and has no managed backups. Export/migrate data before expiration. Free web services block outbound SMTP ports 25, 465 and 587, so SMTP email is not a working free-plan feature; stored contact/volunteer submissions still work. Optional image uploads need Cloudinary credentials. Payments remain disabled.

This is a preview/test deployment, not a claim of production readiness or live-provider verification. Official reference: https://render.com/docs/free

For a new Blueprint, the repository's render.yaml creates the free web service and free database. Do not create a duplicate database if your workspace already has its one allowed free PostgreSQL instance; use the existing-service steps above instead.
