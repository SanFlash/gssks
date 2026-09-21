# Render sign-in and website editing

## What the security token means

CSRF tokens are generated automatically for each browser session. They are not a Cloudinary/Razorpay key, login password or value to copy into Render. An old page can contain an expired token after a sign-out, cookie expiration, or SECRET_KEY change. The application keeps CSRF validation enabled.

HTML pages now use private/no-store caching. Native forms obtain a fresh session-bound token immediately before submission. If an authenticated session expired, the form keeps its text and offers sign-in in another tab. A network failure keeps the form intact and allows a retry. Failed POST requests are never automatically replayed. Without JavaScript, reopening a form generates a fresh token normally.

## Render settings

Use the existing web service and database; do not replace a database that holds organization content.

- Build command: `pip install -r requirements.txt`
- Start command: `python scripts/render_start.py`
- `FLASK_ENV=production`
- `SECRET_KEY`: keep the same private, random value of at least 32 characters across deploys. Do not use a command string or regenerate it on every startup. Changing it signs users out and invalidates open forms.
- `DATABASE_URL`: your PostgreSQL database's internal connection URL. Startup supports `postgresql://`, `postgres://`, or `postgresql+psycopg://` formats.
- `SITE_URL=https://gssks.onrender.com`
- `TRUST_PROXY_HOPS=1` for this Render deployment.
- `INITIAL_ADMIN_EMAIL`: the real administrator's email.
- `INITIAL_ADMIN_PASSWORD`: a private password, 12–128 characters.

Save environment changes and deploy the latest commit. Startup runs migrations, initializes missing official content, and creates the first SUPER_ADMIN if none exists. It never resets an existing admin password. After the first account exists, remove INITIAL_ADMIN_PASSWORD from the service environment. Production demo accounts are disabled.

Open https://gssks.onrender.com/admin/login in a fresh tab. If necessary clear only this site's cookies once, reload, and sign in. Do not submit an old error page or repeatedly press browser refresh on a failed POST. Keep cookies enabled and use HTTPS consistently.

If an admin already exists, use that account. Changing INITIAL_ADMIN_PASSWORD does not reset it. Another SUPER_ADMIN can change the password under Users; the Forgot Password flow requires configured email delivery. Do not delete the database to reset access.

## Give staff the right access

As SUPER_ADMIN open `/admin/manage/users/new`. Enter name, email, a unique password of at least 12 characters, select a role, and enable Active. Share credentials privately.

| Role | Access |
| --- | --- |
| SUPER_ADMIN | All CMS operations plus users and roles |
| ADMIN | Website content, organization settings, projects, media and operational modules; no user/role administration |
| EDITOR | Pages, blog, impact and artisans; not full website settings |
| PROJECT_MANAGER | Projects and events |
| MEDIA_MANAGER | Media and documents |
| VIEWER | No administration access |

Custom grants may be edited by SUPER_ADMIN under Roles. Do not give ordinary content editors user or role administration unnecessarily.

## Where to edit

- `/admin/content-studio`: homepage branding/copy/images, founder, ICPS content and verified recognition.
- `/admin/manage/pages` and `/admin/manage/sections`: editable pages and sections.
- `/admin/manage/projects`, `/admin/manage/events`, `/admin/manage/artisans`: programme records.
- `/admin/manage/blog`, `/admin/manage/gallery`, `/admin/manage/documents`: updates and public media/document records.
- `/admin/settings`: organization/contact/SEO and supported site settings.
- `/admin/media/upload`: organization photos, videos and PDFs. Configure Cloudinary first with CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET in Render. Never publish the secret.

Save changes and check the public page. Records must be published, and associated public documents/media must have public visibility. Existing verification checks for awards and claims still apply. CMS supports its exposed content fields; changes to underlying layouts, code, deployment credentials and new features remain developer tasks.

## Diagnosis if it persists

Check Render logs for `csrf_rejected`, which records the reason and route without passwords or tokens. Confirm the latest deployment is live, cookies are accepted, the SECRET_KEY is stable, and all tabs use the same host. A fresh login GET must return 200 with a session cookie. A token never substitutes for valid credentials or role permissions.

## HTTPS form fix

The former private-page `Referrer-Policy: no-referrer` suppressed a header required by Flask-WTF strict HTTPS CSRF checks. That caused valid tokens to fail on Render while local HTTP checks passed. Private pages now use `same-origin`: same-site submissions retain the header, while external destinations receive no referrer. CSRF and strict HTTPS origin checks remain enabled. Browser QA now runs over TLS with secure cookies. Deploy this correction and reopen the login page; no new token or SECRET_KEY is required.
