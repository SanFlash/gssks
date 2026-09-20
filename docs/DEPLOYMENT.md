# Render deployment

This package contains deployment configuration; it has not been deployed to an account or domain on your behalf. Hosting resources may incur charges. Choose plans in your own Render account before applying the Blueprint.

## Blueprint deployment

1. Create a private Git repository and upload this project, excluding `.env`, virtual environments and `instance/` data. Keep `.env.example`.
2. In Render, choose **New → Blueprint**, connect the repository, and select the branch.
3. Review `render.yaml`: Python web service, PostgreSQL database and Key Value service for shared rate limiting. Adjust plans to account availability.
4. Set `SITE_URL` to your assigned HTTPS origin. Add optional Cloudinary, SMTP and Razorpay environment variables from `CONFIGURATION.md` when ready.
5. The build installs `requirements.txt`. The pre-deploy command applies migrations and initializes configurable organization content without demo accounts.
6. Start uses Gunicorn `run:app` with two workers and four threads. `/health` checks database connectivity.
7. Open Render's private service shell and create the real administrator:

```bash
python -m flask create-admin
```

Passwords are hidden while typing in this command; that is normal. Enter at least 12 characters, press Enter, and confirm. Never reuse a demo password.

8. Sign in at `/admin/login`, complete the nine-step setup, upload approved branding and replace draft content.
9. Add a scheduled task/worker to execute `python -m flask send-email` every minute if SMTP is enabled. Use the same database and mail variables.
10. Complete the staging verification checklist before enabling live donations or announcing the site.

`render.yaml` includes a pre-deploy command, which may require a paid service plan. For a plan without pre-deploy support, run migration/content initialization as a controlled deployment step before starting the new application version. Do not place destructive schema rebuilds in startup code.

## Manual web service

- Runtime: Python, `PYTHON_VERSION=3.13.15` (or an organization-approved tested 3.13.x patch).
- Build: `pip install -r requirements.txt`
- Pre-deploy: `python -m flask db upgrade && python -m flask init-content`
- Start: `gunicorn --workers 2 --threads 4 --timeout 60 --bind 0.0.0.0:$PORT run:app`
- Health: `/health`
- `FLASK_APP=run:app`, `FLASK_ENV=production`.
- Random `SECRET_KEY`, PostgreSQL `DATABASE_URL`, HTTPS `SITE_URL` and shared `REDIS_URL`.

The application normalizes `postgres://` and `postgresql://` URLs to SQLAlchemy's `postgresql+psycopg://` dialect. Production has no persistent local-upload requirement. Do not use SQLite on ephemeral web-service disks.

## Production gate

- A genuine admin exists; demo users cannot sign in.
- Published legal pages, contacts, privacy retention policy and refund terms have organization approval.
- No sample records appear publicly.
- PostgreSQL migration upgrade and backup restore succeed in staging.
- Redis is reachable by all workers. Do not use `memory://` across multiple production workers.
- Sign-in cookies are Secure/HttpOnly/SameSite. HTTPS and canonical domain match.
- Private PDF downloads are restricted. CDN credentials are absent from rendered HTML.
- SMTP queue is drained by a configured worker; reset mail arrives.
- Test-mode Razorpay capture, webhook retry and full refund pass before live keys are installed.
- Verify gateway checkout with the delivered Content Security Policy; add only provider-documented hosts if your checkout account needs additional origins.
- Check actual-device navigation and a deployed Lighthouse run. Targets are not certified results.

## Operations

Use your provider's backups and alerting for availability, elevated 5xx responses, mail queue growth and payment/webhook failures. Audit logs record actor, action, entity, ID, timestamp and observed source IP. Configure trusted proxy handling only for a known deployment topology; do not blindly trust client-supplied forwarding headers. Set `TRUST_PROXY_HOPS` to the verified number of trusted proxy hops (default `0` disables forwarded-header trust). Verify source IPs and HTTPS detection in staging before adjusting it.

For updates: stage migrations first, back up, deploy compatible changes, verify `/health`, sign in, create/edit an unpublished record, exercise a contact submission, and check the webhook endpoint. Roll back code only when compatible with the current schema. Test restoration in a separate database before relying on a backup.

Official provider reference: https://render.com/docs/blueprint-spec
