# Testing and verification

## Recorded result

- Python: **3.13.15**; all direct runtime imports passed.
- Automated backend/adapter suite: **125 passed**.
- Browser: **25 responsive route/width checks passed**, plus mobile navigation, sign-in, admin/editor, public demo filtering, and contact/volunteer submissions.
- SQLite: initial migration applied; migration drift check reported no new operations.

## Automated functional tests

```bash
pip install -r requirements-dev.txt
python scripts/verify_runtime.py
python -m pytest -q
```

The suite uses an isolated SQLite database and mocks external provider responses. It checks public routes, admin list/create screens, authentication, granular permissions, published content, project CRUD, enquiries, volunteer duplicate handling, event capacity, CSRF, login cooldown, single-use resets, private documents, upload validation/limits, CSV injection, safe error pages and payment signature/capture/amount/idempotency logic. Cloudinary adapter tests check upload/replace/delete without an external account.

`runtime-verification.json` contains the actual Python/dependency import results. `test-results.txt` and `browser-results.json` record the completed run. These are test evidence, not a blanket production certification.

## Browser smoke tests

```bash
python -m playwright install chromium
# Linux/macOS:
PYTHONPATH=. python scripts/browser_check.py
# PowerShell:
# $env:PYTHONPATH = '.'
# python scripts/browser_check.py
```

The browser script starts an isolated temporary-database WSGI server and uses Chromium. It tests widths 320, 360, 375, 390, 414, 430, 480, 768, 820, 1024, 1280, 1366, 1440, 1600, 1920 and 2560 on the homepage; checks representative secondary mobile routes; exercises navigation, login, admin, rich editor, public demo filtering and contact/volunteer submission. Screenshot evidence is saved under `docs/screenshots/`.

The deterministic test blocks external asset requests and uses reduced motion, verifying that the site remains usable without Google Fonts or remote animation libraries. This is not a test of live WebGL/CDN or payment checkout.

## Live integration acceptance

Before public launch, in a staging deployment with test credentials:

| Area | Acceptance check |
|---|---|
| PostgreSQL | Apply the migration; create/update relational records; restore a backup into a separate DB. |
| Roles | Test each staff role; direct URL/API attempts must not reveal unauthorized records. |
| Cloudinary | Upload real JPEG/PNG/WebP, MP4/WebM, private/public PDF; replace and delete; check signed-link expiry. |
| Razorpay | Test successful capture, cancellation, failure, amount mismatch, webhook retry, browser closure and refund. |
| SMTP | Confirm delivery of every template, especially password reset and donation receipt; check retry/queue processing. |
| Devices | iPhone/Safari, Android/Chrome, iPad/tablet and desktop keyboard tests. |
| Accessibility | 200% zoom, focus order, reduced motion, screen reader, meaningful alt text and contrast with final branding. |
| Motion | Reduced-motion mode and subtle CSS transitions; the client redesign does not load the optional WebGL scene. |
| Performance | Run Lighthouse on the deployed origin with realistic approved images; aim for 90+ in each requested category. |
| Privacy | Review final legal text, retention, consent, private receipts, PDF visibility, exports and analytics opt-in. |

Lighthouse scores, real mobile-device results, live gateway results and an independent security audit are **not claimed** by local tests. Record those results separately after account-specific configuration.

## PostgreSQL CI

`.github/workflows/verify.yml` defines a Python 3.13 job with an isolated PostgreSQL 16 service. It applies/checks migrations and runs the functional suite against both SQLite and PostgreSQL. This workflow is supplied but has not been executed in your GitHub account.

You can run the same suite against a **disposable test database only** by setting `TEST_DATABASE_URL`. The fixture creates and drops all application tables. Never point that variable at production or a database containing records you need to retain.

Local startup regression: fresh temporary checkout, no .env or database, `python run.py` creates both and serves HTTP 200. Repeat initialization preserves users and configuration. Production and remote databases are rejected by automatic local setup.
