# Client brief revision

See [CLIENT_UPDATE.md](CLIENT_UPDATE.md) for the updated design, sitemap, supplied facts, content import, admin workflow and remaining publication inputs.

# Release scope and launch gates

This is a runnable source release, not a claim of completed production certification or a live deployment.

## Included

The public website, admin workspace, relational schema/migration, configurable content, eight roles with permission checks, media adapter, event/volunteer/contact workflows, newsletter records, payment verification/receipts/refunds, email outbox, exports, error handling, SEO, responsive styling and motion fallbacks are implemented in source. Setup, seed, runtime verification, test suite, browser checks and Render Blueprint are included.

Local images are original abstract vector craft motifs. They are not photographs of the NGO, beneficiaries or real artisans. Replace them with approved organization media from the CMS. Google Fonts and pinned motion libraries load as optional external enhancements. Without them, the website uses local fallbacks.

## Confirmed locally

See the runtime, automated-test and browser-result files in this folder. Python 3.13 imports and SQLite migration execution were checked. Browser evidence covers desktop and mobile layouts, with reduced motion and external assets deliberately disabled.

## Requires account-specific acceptance

- Real Cloudinary uploads/private delivery, SMTP delivery and Razorpay test-mode checkout/capture/webhooks/refunds.
- PostgreSQL runtime/restore checks (CI workflow supplied), Redis multiworker behavior and the actual Render deployment.
- Organization-approved content, media, legal details and policies.
- Real-device Safari/iOS/Android testing, deployed Lighthouse measurements and independent security/accessibility review.

No Lighthouse score or independent audit result is asserted. The 90+ targets remain launch acceptance criteria.

## Deliberate implementation choices

- Payment status is server-owned; administrators cannot edit a donation to “Paid.”
- Receipts are printable HTML with the browser's PDF export, not a separate binary PDF generator.
- SMTP jobs are durable but require the documented scheduled outbox command.
- Secrets are environment-owned. The admin wizard edits organization content and provides integration setup instructions; secrets are not stored as CMS content.
- Sample records and demo identities remain blocked in production even if the same database is reused.
- Same-origin APIs need no permissive CORS package.
- A nine-step wizard reflects the nine steps in the brief.
- Impact timeline dates are editor-supplied; no foundation date is inferred.
- Generic CMS fields map blog excerpt/body to `short_description`/`description` and artisan name/biography to `title`/`description`.
- Pending payment capture and gateway errors are visible states, not simulated successes.

Optional donor self-registration/history, recurring donations, Stripe, PWA, map, marketplace, AI, CSR workflow automation and multilingual functionality are outside this release. Their addition does not require replacing the existing architecture.
