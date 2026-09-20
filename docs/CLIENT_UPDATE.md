# GSSKS client brief update

## What changed

- Official display name: Gyan Path Shiksha Evam Samaj Kalyan Samiti (GSSKS).
- Client-supplied establishment year (1992), M.P. Government recognition, registration (1262/92), address, landline, mobile and email are configurable organization settings.
- Ten primary destinations: Home, About Us, Our Work, Projects, Impact, Gallery, News & Events, Get Involved, Documents, Contact Us. Existing deeper routes remain available.
- An editorial forest-green/ivory design, restrained motion, accessible mobile navigation, contact-first calls to action and an approval-aware gallery replace the previous demo-led homepage.
- Gandhi Shilp Bazaar is a real CMS project record with supplied dates, venue, 50 artisans and ₹14,95,577+ reported exhibition sales. These sales are neither donations nor lifetime impact. Outcomes remain editable through Projects.
- News & Events combines the existing blog and event systems. Get Involved connects to working volunteer and contact forms.
- Sample records remain available in the administrator interface but are excluded from public queries by default in every environment. Production always excludes them, including APIs, search and sitemap.
- Existing Flask blueprints, relational schema, role-based admin, Cloudinary, forms, payment verification, privacy controls and deployment structure are retained. No schema migration is required for this update; the existing migration remains included.
- A repeatable content import is separate from schema migration. Homepage claims and organization details come from settings/project records. No new partner, beneficiary, mission or vision claims are generated.

## Upgrade an existing installation

Back up the database and uploaded-asset references first. Replace application source while preserving `.env`, the database and existing secrets. With the virtual environment active:

```bash
python -m flask db upgrade
python -m flask apply-client-brief
python run.py
```

`apply-client-brief` refreshes the supplied official organization settings and About page, creates Gandhi Shilp Bazaar if absent, and unpublishes demo content. It does not delete sample records, custom projects, media or accounts. An existing Gandhi Shilp Bazaar record is preserved, including administrator-edited outcomes. Review existing custom pages and publication settings before launch. The command is an intentional content refresh; do not run it after modifying those organization facts unless you want to reapply the supplied brief.

Fresh installations can follow `README.md`; normal seeding includes these official facts and project automatically. Demo accounts remain development-only. `SHOW_DEMO_CONTENT=True` is an internal test-only application configuration; no public query parameter enables demo content.

## Updating through admin

- Organization setup: name, establishment, recognition and registration.
- Contact setup: address, phone, mobile, email and an approved map URL.
- Homepage setup: heading, introductory copy and footer description.
- Branding setup: approved logo, favicon and hero photograph.
- Projects: Gandhi Shilp Bazaar dates, location, outcomes, description, project images and public documents.
- Gallery / Media: upload approved images, supply meaningful captions/alt text and publish selected gallery records.
- Blog / Events: publish organization-approved announcements and event details.
- Documents: upload PDFs and explicitly select public visibility for approved downloads.
- Pages: edit official About, work-area descriptions, mission and vision when provided.

## Publication needs

The supplied facts are attributed to the organization; independent government verification is not implied. Obtain the official logo, approved photographs, mission/vision/objectives, full work descriptions, supporting reports, document publication permissions, verified social profiles and exact map link before final publication. The site labels decorative artwork and missing photographs. No unrelated photograph is presented as evidence of NGO work.

The supplied mobile number is retained verbatim. WhatsApp remains hidden unless separately confirmed and configured. Donation/payment integration remains disabled until configured; no bank details, tax exemption or partner logos have been invented. Legal draft pages require organization review before live personal-data collection.
