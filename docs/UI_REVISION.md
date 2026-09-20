# Changes.pdf implementation

The final portion of the 29-page client brief takes precedence over its earlier suggestions. The implementation follows its blue/red/white identity, ICPS emphasis, founder-specific recognition and UI-first scope.

## Public UI

- Colors: #182B78, #B52E35, white, #F7F7F4, #EEF2FA and #FAEEEE. DM Serif Display headings and DM Sans body with system fallbacks.
- Navigation: Home, About, ICPS, Our Work, Recognition, Gallery, Documents, Contact and Get Involved. Older project/impact/news routes remain accessible through relevant sections and footer.
- Homepage: editorial hero, institutional strip, ICPS feature, six work areas, founder, recognition, contextual impact, secondary exhibition case study, gallery, documents and participation.
- Dedicated ICPS and leadership/recognition pages. Gandhi Shilp Bazaar remains a secondary initiative. No invented child beneficiary counts, locations or responsibilities.
- Gallery filters are based on published categories. PDF document cards, certificate dialog with keyboard dismissal and a direct-open fallback.
- Real-photo slots remain explicit empty states until the organization provides approved imagery. No generated or stock child imagery is used.

## Admin access

Sign in at `/admin/login`, then open **Website studio** in the sidebar (`/admin/content-studio`).

| Editor | Purpose |
|---|---|
| Branding & homepage | Logo, hero photo/alt text, heading, subtitle and introductory copy |
| Founder & leadership | Name, role, biography and portrait |
| ICPS feature | Homepage summary and programme photograph |
| ICPS programme page | Main page title, description and publication status |
| ICPS content sections | Role, children supported, interventions, approach, locations, impact and documentation |
| Recognition | Exact award names, years, authorities and public certificate document IDs |
| Private source review | Notes about the PDF's linked sources and publication limitations |
| Gallery / Documents / Impact | Existing permission-checked content managers |

Settings editors require settings.manage; page editors require page.edit. Public certificates require complete verified metadata plus a public PDF document and public media asset. Making either private automatically hides its certificate link. Empty award particulars never generate a certificate button. Awards are attributed to I. S. Chauhan, not the organization.

## Source decisions

1. **Changes.pdf**, final correction: I. S. Chauhan is Founder & Director. This supersedes the earlier business card's President title. Biography remains limited to the supplied founder statement. Award names, years and authorities were not supplied.
2. [Linked Scribd audit report](https://www.scribd.com/document/1068052435/MP-Report-No-2-of-2026-English-06a61c242e0da69-34500633): readable, references Gyan Path in child-care/open-shelter context. It contains adverse audit findings and contested occupancy reporting. It is not a recognition certificate or a reliable source for a celebratory “100 children supported” counter. No such figure or government endorsement was imported. The primary report and organization response need review before publishing further claims.
3. [Handicrafts PDF](https://handicrafts.nic.in/pdf/dc_hc_GIA1314.pdf): attempts returned a timeout/502. No empanelment, grant, partnership or extra project was inferred from its filename.
4. Changes.pdf repeatedly cites another exhibition report by filename, but that original report and its photographs were not included in this upload. Existing organization-supplied Gandhi Shilp Bazaar facts remain; requested photos and certificates must be provided separately.

Both links and review notes are saved in an unpublished CMS Page, accessible to authorized page editors. It is excluded from public pages, search and sitemap until deliberately published. No external report was copied or republished as an organization-owned document.

## Deployment

The existing Render Free startup remains intact. `python scripts/render_start.py` applies migrations and seeds official content before Gunicorn. This revision needs no schema migration: it extends existing organization settings, pages, page sections, documents and permissions. Content initialization adds missing fields/pages and upgrades only matching previous default hero/footer copy. Administrator-customized values are retained. Existing deployments using another start command must run `python -m flask init-content` once.

Exact award details, founder portrait, child-protection programme descriptions, approved photos and certificate PDFs remain organization inputs. Detailed new user-flow design is deferred as instructed in the brief.
