# Configuration and integration guide

## Required production values

| Variable | Meaning / source | Example |
|---|---|---|
| SECRET_KEY | Generate locally using `python -c "import secrets; print(secrets.token_hex(32))"` | 64 random hexadecimal characters |
| DATABASE_URL | PostgreSQL connection string from Render database settings | `postgresql+psycopg://user:password@host/database` |
| SITE_URL | Your actual HTTPS domain | `https://your-ngo-domain.example` |
| REDIS_URL | Shared Redis/Render Key Value URL | `redis://host:6379` |

Never use `change-me`, demo passwords or SQLite for public production. Do not send credentials in chat or commit `.env`.

## Cloudinary

1. Create a Cloudinary account or use the organization's existing account.
2. Get **cloud name**, **API key** and **API secret** from the Cloudinary console.
3. Set `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` in `.env` locally or the Render environment in production.
4. Restart the application. Run `python -m flask check-config`; it displays readiness booleans, not secrets.
5. Sign in to Admin → Media → Upload media.
6. Choose image/video/PDF, an approved folder and visibility.
7. Upload a small test PNG, replace it, verify the public page, then delete the unused test asset.
8. Test a private PDF: an anonymous user must not be able to obtain a download link.

Folders use `gyanpath/branding`, `hero`, `projects`, `artisans`, `events`, `gallery`, `videos`, `documents`, `blog`.

Images: JPEG, PNG or WebP, up to 10 MB and 24 megapixels. Videos: MP4/WebM up to 25 MB. Documents/resumes: PDF up to 5 MB. Cloudinary plan restrictions may be more restrictive; PDF delivery may need enabling in its security settings.

Only public asset URLs can be copied from the UI. Private uploads use Cloudinary's authenticated delivery type. Their download links are signed with a short expiration after the application authorizes the request. A public document also requires public underlying media; changing only a database label cannot convert a private asset into public delivery.

Remote URL mode is administrator-only. Configure `REMOTE_MEDIA_HOSTS` to approved image/CDN hostnames, without schemes. No background download of arbitrary URLs occurs. The administrator is responsible for supplied content permissions. YouTube and Vimeo URLs are embedded, never downloaded.

If Cloudinary is absent, local abstract craft artwork remains usable. You may configure an approved remote cover/hero URL from the admin. Missing remote images fall back to the local illustration.

Official reference: https://cloudinary.com/documentation/python_integration

## Razorpay

1. Use an organization-owned Razorpay account. Complete its account requirements before considering live collection.
2. Generate **test-mode** keys in the Razorpay dashboard.
3. Set:

```dotenv
RAZORPAY_KEY_ID=rzp_test_your_key_id
RAZORPAY_KEY_SECRET=your_private_test_secret
RAZORPAY_WEBHOOK_SECRET=your_separate_random_webhook_secret
DONATIONS_ENABLED=true
```

4. Configure automatic capture in the gateway account. An authorized but uncaptured payment is not treated as paid by this app.
5. Add the webhook URL `https://YOUR_DOMAIN/api/donations/webhook`. Use the matching webhook secret and subscribe to `payment.captured`, `order.paid`, `payment.failed` and `refund.processed`.
6. Complete a small payment using Razorpay's documented test payment details. No real card details belong in your local configuration or database.
7. Verify the donation is Paid, a single receipt exists, and its amount/order/payment IDs match the dashboard.
8. Send the same webhook again: no duplicate receipt should appear.
9. Try a changed signature and amount mismatch in tests: neither may become Paid.
10. Test a refund through a FINANCE_MANAGER/SUPER_ADMIN account. Processed full refunds are shown as Refunded. Pending refunds remain Paid until the gateway confirms processing.
11. After staging checks, replace with approved live keys in the host environment. Do not change application source.

The frontend receives only the publishable key ID, order details and a random donation receipt token. The private key remains server-side. Receipts use an unguessable capability URL, `Cache-Control: no-store` and `Referrer-Policy: no-referrer`. Treat a receipt link as private; anyone you share it with can view that receipt.

Optional PAN storage requires `FIELD_ENCRYPTION_KEY`. Generate it with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Without it, donations can proceed with PAN blank. PAN is encrypted and excluded from CSV exports. Keep the key in your secret manager; losing it makes existing PAN values unreadable. No tax exemption is implied by PAN collection or receipt generation.

Official references:
- https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/
- https://razorpay.com/docs/webhooks/validate-test/

## SMTP and queued mail

Use an organization-approved SMTP provider:

```dotenv
MAIL_SERVER=smtp.example.org
MAIL_PORT=587
MAIL_USERNAME=your_smtp_username
MAIL_PASSWORD=your_smtp_password
MAIL_USE_TLS=true
MAIL_DEFAULT_SENDER=notifications@your-domain.example
```

Verify your sender/domain with the provider as required. The app uses STARTTLS on port 587 by default. Do not place SMTP secrets in organization content fields.

Email templates cover enquiry acknowledgement, volunteer application/approval, event registration, donation receipt, password reset and admin notification. Jobs are written in the same database transaction as their corresponding operation.

Deliver queued messages:

```bash
python -m flask send-email
```

Schedule this command every minute in a private worker/cron process with the same application code, database URL and SMTP environment. The web service alone does not continuously drain the queue. The command uses PostgreSQL row locks and `skip_locked` to avoid simultaneous workers processing the same batch. Delivery is at-least-once; an SMTP failure after acceptance may produce a duplicate if retried.

When SMTP is missing, local logs report that mail was queued **without printing recipient data or reset links**. The private `email_job` database table contains development messages; inspect it locally if needed. Never expose this table through a public endpoint.

## Organization setup

Admin → Settings updates official name, location, contact information, logo/favicon/hero image, homepage content, footer, legal registrations, SEO description and maintenance mode. Social links are under Admin → Social. Empty socials/WhatsApp remain hidden.

Integration secrets are environment-owned on purpose; the setup wizard explains where to obtain and set them. Editorial content changes do not require a developer.

Set maintenance to the literal `true` or `false`. The public site returns 503 during maintenance; sign-in, admin and signed payment webhooks remain reachable.

## Optional analytics

Set `GA_MEASUREMENT_ID=G-YOURID` to enable the opt-in banner. No analytics script is requested until the visitor allows it. Private/admin/auth/receipt pages never load analytics, and submitted query strings are not sent as page locations. Google Analytics remains a third-party processor; reflect its use in the organization's approved policy. Clear the local `gyanpath-analytics` preference to show the choice again during testing.
