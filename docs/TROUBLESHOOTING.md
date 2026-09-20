# Troubleshooting

## Password typing appears blank

The `flask create-admin` terminal command uses hidden password entry. Keystrokes are accepted even though no characters or asterisks appear. Type the password, press Enter, then confirm. Local `scripts/setup.py` avoids password prompts and uses the configurable demo accounts.

## Demo login fails

1. Ensure the terminal is in the directory containing `run.py`.
2. Activate the Python 3.13 environment.
3. Check that `.env` exists and contains all six `DEMO_*` values.
4. Run `python -m flask db upgrade`, then `python seed.py`.
5. Use the actual values in `.env`. Demo login is disabled if `FLASK_ENV=production`.
6. After five incorrect attempts, wait 15 minutes. Reset the password through the supported reset workflow rather than editing hashes manually.

Seeding does not overwrite an existing user's password. Changing `.env` after a user has been created does not reset that account. Use the password reset link with configured SMTP, or create a separate named admin through the private CLI.

## “Configuration required” page

Development: database tables may not exist. Run `python -m flask db upgrade`, then `python seed.py`.

Production: check the random secret, PostgreSQL URL, successful migrations and database connection. Do not bypass the production gate by switching a public service to development mode.

## CSRF error / refresh page

Refresh the form, then submit it again. Tokens expire after two hours and sessions after 45 minutes. Ensure the browser accepts cookies. Use one hostname consistently (`127.0.0.1` versus `localhost`). Production must use HTTPS because cookies are Secure. A reverse proxy must preserve the expected request origin.

For JSON POSTs, obtain a token from a rendered page's `meta[name=csrf-token]`, keep the same session cookie and send `X-CSRFToken`. The signed Razorpay webhook has its own HMAC verification and does not use browser cookies.

## Flask imports fail

Check `python --version` and `python -m pip --version`; both must point to the same virtual environment. Install `requirements.txt` and run `python scripts/verify_runtime.py`. Use `python -m flask`, not an unrelated globally installed `flask` command.

## Windows Gunicorn error

Gunicorn is the Linux production server. Use `python run.py` on Windows. Deploy the source to Render for Gunicorn operation. Do not run Gunicorn as the local Windows development server.

## Form validation errors

Read the inline message. Slugs must be lowercase words separated by hyphens. Volunteer age is 18–120; phone accepts common international formatting. Consent is mandatory. Event end time must follow its start time, project end date cannot precede its start date, and capacity cannot be reduced below the number registered.

## Media unavailable / cannot upload

Configure Cloudinary and restart. Check the correct file type, MIME and size limits. A renamed executable is rejected. Raw PDFs may require account-level delivery settings in Cloudinary. Private media cannot be selected for a public gallery or public document. If the provider is unavailable, retry rather than changing visibility to bypass protection.

Deleting media referenced by a project, gallery, report, resume or organization branding is blocked. Remove its references first. Replacing media keeps the database asset ID and updates direct cover/branding references.

## No email arrives

Run `python -m flask check-config`, verify SMTP sender credentials, then `python -m flask send-email`. Configure a recurring worker/cron job. Check the private outbox for Pending records and attempt counts. No SMTP configuration means messages remain in the local outbox; a queued confirmation is not evidence of delivered email.

## Donation remains Pending

Do not manually mark it Paid. The server requires a valid signature and a captured Razorpay payment with matching amount, currency and order. Check capture configuration and webhook delivery in the gateway dashboard. The browser offers a retry-verification action if a capture has not settled. Configure signed webhooks so closing the browser does not lose reconciliation.

## Empty production content

Demo records are intentionally hidden in production. Create real records or replace verified content and clear `Is demo`, then publish with the appropriate permission. Seed production defaults with `python -m flask init-content`, not `seed.py`.

## 429 Too Many Requests

Wait for the rate-limit window. In multiworker deployment, configure a shared Redis store. Never disable production rate limiting to avoid a configuration problem.

## Browser QA

Install `requirements-dev.txt`, then `python -m playwright install chromium`. Run from the project directory:

```bash
# Linux/macOS
PYTHONPATH=. python scripts/browser_check.py
```

PowerShell:

```powershell
$env:PYTHONPATH = '.'
python scripts/browser_check.py
```

The script uses a temporary SQLite database, a local test server on port 5099 and synthetic demo data. Close anything already using that port. It does not send real email or payments.
