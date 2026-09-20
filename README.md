# GSSKS — Gyan Path

**Education • Awareness • Empowerment**

Flask / Jinja2 website and management platform for **Gyan Path Shiksha Evam Samaj Kalyan Samiti (GSSKS)**, Bhopal, Madhya Pradesh, India.

The application includes a public website and a separate permission-controlled admin workspace. Organization information is configurable. Sample records are clearly marked **DEMO CONTENT** and excluded from public queries by default in every environment. No registration, government association, certification, tax exemption or impact number is invented.

## Client brief update

The site includes the supplied organization details and Gandhi Shilp Bazaar project. See [the update and upgrade guide](docs/CLIENT_UPDATE.md). Existing installations: back up the database, run `python -m flask db upgrade`, then `python -m flask apply-client-brief`. Official photographs and final organization content remain subject to approval.

## Start locally on Windows

Install Python **3.13.x**, extract this project, and open a terminal in the folder containing `run.py`.

PowerShell:

```powershell
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```

If PowerShell prevents activation, use the interpreter directly; no execution-policy change is necessary:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe run.py
```

Open **http://127.0.0.1:5000**. Admin login: **http://127.0.0.1:5000/admin/login**.

`python run.py` now automatically creates a missing `.env`, generates a local secret, applies database migrations and seeds development accounts before starting the website. Repeated starts preserve existing settings, accounts and records. No Cloudinary, SMTP or Razorpay credentials are required. Local startup uses SQLite and refuses production/remote-database auto-initialization. `scripts/setup.py` remains available for manual setup. Production WSGI imports do not auto-seed.

## Start locally on Linux or macOS

```bash
python3.13 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```

## Manual setup

If using Git, first clone your own repository containing this source and `cd` into its root. No repository URL is assumed or hardcoded.

```bash
# After creating and activating the virtual environment:
pip install -r requirements.txt
cp .env.example .env  # Windows: Copy-Item .env.example .env
python --version
python scripts/verify_runtime.py
python -c "import flask; from importlib.metadata import version; print(version('Flask'))"
python -m flask db upgrade
python seed.py
python run.py
```

The migration repository is already included. **Do not run `flask db init` for initial installation.** For future model changes in a development branch:

```bash
python -m flask db migrate -m "Describe the schema change"
python -m flask db upgrade
```

`python -m flask db init` is only for a new project without the included `migrations/` directory.

## Development-only accounts

| Role | Email | Password |
|---|---|---|
| SUPER_ADMIN | admin.demo@gyanpath.local | Gyanpath@Demo2026! |
| EDITOR | staff.demo@gyanpath.local | Gyanpath@Demo2026! |
| VIEWER | user.demo@gyanpath.local | Gyanpath@Demo2026! |

These values come from `.env.example`, not hardcoded authentication logic. `seed.py` reads the environment variables. Existing accounts are never silently overwritten. A VIEWER can sign in but cannot enter the admin workspace. Production rejects all users marked `is_demo`, even if a development database was copied accidentally.

First administrator login opens a **nine-step** organization setup wizard. The brief lists nine steps, so the progress indicator correctly uses `1/9` through `9/9`.

## What is implemented

- Responsive public pages, projects, artisan profiles, events, blog, galleries, documents, impact stories, FAQs, volunteer applications, enquiries, newsletter subscriptions and search.
- Forest-green/ivory editorial design, labelled decorative craft artwork, restrained CSS transitions, reduced-motion handling and keyboard/swipe gallery viewer. The earlier optional 3D module is retained in source but is not loaded by the redesigned homepage.
- Application factory, four Flask blueprints, SQLAlchemy models, Alembic migration, SQLite development / PostgreSQL production configuration.
- Admin content CRUD, categories, project images, galleries, page sections, menus, roles, granular permissions, organization settings, audit logs, search, sorting, CSV exports, charts and recent activity.
- Authenticated sessions, password hashing, CSRF, login cooldown, rate limits, single-use password resets and session invalidation after password changes.
- Cloudinary upload, replace, delete, metadata editing, public/private assets, protected downloads, validation and approved remote media URLs. YouTube/Vimeo embeds are supported through **Media → Add remote URL**.
- Event registrations with an atomic capacity check and uniqueness per event/email. Volunteer review with approved/rejected status, resume download and contact action.
- Razorpay orders, HMAC signature checks, server-side capture/amount/currency/order validation, idempotent receipts, signed webhooks and permission-gated refund requests. No payment is accepted solely on a frontend success event.
- SMTP templates with a durable outbox; administrator activity notifications are shown in the dashboard.
- SEO descriptions, canonical/Open Graph/Twitter metadata, organization/article/event/breadcrumb structured data, sitemap and robots rules.
- Error pages/JSON errors, maintenance mode, print-to-PDF donation receipts, private operational exports, runtime/import checks, automated tests and browser smoke script.

Optional donor self-registration/donation-history accounts, recurring donations, Stripe, marketplace checkout, map, PWA, AI features and multilingual support are not enabled. These were optional or future expansion items in the brief. The basic VIEWER account is intentionally not a donor portal.

## Architecture and files

```text
gyanpath_ngo/
├── app/
│   ├── __init__.py           # Application factory, errors, headers
│   ├── config.py            # Environment validation and safe defaults
│   ├── extensions.py        # Database, auth, CSRF, cache, limiter, mail
│   ├── cli.py               # Roles, seeding, create-admin, email worker
│   ├── models/__init__.py   # Domain models and relationships
│   ├── forms/__init__.py    # Public server-side validators
│   ├── public/__init__.py   # Public website routes
│   ├── auth/__init__.py     # Authentication and password resets
│   ├── admin/               # Admin routes, field allowlist, forms
│   ├── api/__init__.py      # JSON APIs and signed webhooks
│   ├── services/            # Payments, media, mail, content, applications
│   ├── utils/security.py   # Permissions, sanitization, URL policy, CSV
│   ├── templates/          # Public/admin/auth/errors/email templates
│   └── static/             # CSS, JavaScript, local illustrations/icons
├── migrations/             # Checked-in initial Alembic revision
├── tests/                  # Functional, security and adapter tests
├── scripts/                # Setup, runtime verification, browser QA, backup
├── docs/                   # Integration guides, test evidence, screenshots
├── instance/               # Local data; excluded from release archive
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── render.yaml
├── Procfile
├── runtime.txt
├── run.py
└── seed.py
```

## Environment variables

See `.env.example` and [configuration guide](docs/CONFIGURATION.md) for sources and examples. Optional integrations do not prevent the website running.

| Variable | Use | Required |
|---|---|---|
| FLASK_APP | `run:app` | CLI |
| FLASK_ENV | `development` / `production` | Production |
| SECRET_KEY | Random secret, 32+ characters | Production |
| DATABASE_URL | SQLite or PostgreSQL URL | Production |
| SITE_URL | Canonical public HTTPS origin | Production |
| REDIS_URL | Shared rate-limit store | Multiworker production |
| CLOUDINARY_* | Media provider credentials | Uploads |
| MAIL_* | SMTP host, account, sender and TLS | Email delivery |
| DONATIONS_ENABLED | Default `false` | Payments switch |
| RAZORPAY_KEY_ID / KEY_SECRET | Server-side gateway credentials | Payments |
| RAZORPAY_WEBHOOK_SECRET | Webhook HMAC secret | Payment reconciliation |
| FIELD_ENCRYPTION_KEY | Fernet key for optional PAN storage | Only if PAN collected |
| REMOTE_MEDIA_HOSTS | Comma-separated approved image/CDN hosts | Remote media |
| GA_MEASUREMENT_ID | Optional analytics identifier | Only if analytics enabled |
| DEMO_* | Configurable development accounts | Demo seeding |

Production with missing core configuration returns a **Configuration required** page rather than exposing an insecure setup endpoint. The database is never automatically rebuilt by HTTP requests.

## Admin working steps

1. Sign in as the demo admin and complete the setup wizard.
2. Add official contact details, approved social links and branding.
3. Upload a public image through **Media**; copy its public URL for project/article covers. Keep documents and resumes private unless explicitly approved for public release.
4. Create categories, then add projects, artisans, events and articles. Keep `Published` off while drafting. Keep `Is demo` on for any sample content.
5. Add public gallery entries, connect them to media, and use project images to attach project galleries.
6. Edit About, Mission, Vision and focus pages under **Pages**. Add ordered content blocks under **Sections**. Configure footer and homepage text under **Settings**.
7. Enter verified impact numbers under **Statistics** and enable `Verified`. Zero/unverified values display “Data to be updated.” Manage dated/undated timeline entries under **Stories**.
8. Review volunteer applications and contact enquiries. Approval queues an email. The **Contact** action opens your configured mail client; **Replied** tracks your follow-up.
9. Review event registrations, donations and subscriber records. Export authorized datasets as CSV.
10. Create individual staff users with least-privilege roles. Only SUPER_ADMIN can change users or roles; no role editor can grant itself elevated access.

## Database, backups and privacy

Development data is stored under `instance/gyanpath.db`. Production uses PostgreSQL and external Cloudinary media. No binary uploads are stored in the database.

Local backup:

```bash
python scripts/backup_sqlite.py /private/path/gyanpath-backup.db
```

For PostgreSQL, use the provider's managed backups and `pg_dump` / `pg_restore` from a private operator environment. Test restore into a separate staging database. Keep `SECRET_KEY`, the PAN encryption key and Cloudinary recovery information in your secret manager; rotating the encryption key requires decrypting/re-encrypting existing PAN values before replacing it.

Operational CSV exports are not full database backups. They prevent spreadsheet formula injection and never include password hashes, gateway signatures, PAN, session identifiers or private media URLs.

Review privacy, consent, retention, refund terms and organization contact details before collecting real personal data. Supplied legal page text is explicitly marked as a draft requiring organization review.

## Integrations and deployment

- [Cloudinary, Razorpay and SMTP setup](docs/CONFIGURATION.md)
- [Render deployment guide](docs/DEPLOYMENT.md)
- [Testing and verification](docs/TESTING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Implementation scope and launch gates](docs/RELEASE_NOTES.md)

## Security design

Browser mutations and JSON POSTs require a CSRF token. Only the Razorpay webhook is exempt; it requires a valid raw-body HMAC. CORS is deliberately same-origin, with no wildcard credentialed access. No remote URL is fetched by the backend merely because a visitor submits it.

Rich text is sanitized on save and render. Queries use ORM expressions. Admin fields and actions are explicitly allowlisted. Private assets use authenticated Cloudinary delivery and authorization-checked short-lived download links. Upload validation checks extension, claimed MIME, actual image/container signatures and limits; PDF active-content checks are conservative screening, not a malware scanner.

Password reset links expire after 30 minutes and become invalid after the first successful reset. Five failed login attempts trigger a 15-minute cooldown. Session duration is 45 minutes. Cookies use HttpOnly/SameSite and Secure in production. Log output omits exception values that might contain personal information.

### Verification limits

Local tests do not certify live provider configuration, accessibility conformance, security audit completion or a Lighthouse score. Complete the staging/provider checks in `docs/TESTING.md` before public launch. Do not describe this release as independently certified or already deployed.
