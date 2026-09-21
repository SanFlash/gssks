# Public animation enhancements

The animation layer preserves the approved content, logo, blue/red palette, ICPS hierarchy, founder attribution and all CMS settings. No organizational claims or data were added.

- Local Canvas geometry and floating points behind the homepage hero.
- Staggered headline entrances and viewport-triggered section/card reveals.
- Fine-pointer card perspective, button feedback and navigation underlines.
- Gallery image hover and a reading progress indicator.
- Footer animation pause/resume control with local preference persistence.
- Live operating-system reduced-motion support; no scroll hijacking.

The layer uses local JavaScript, CSS and native browser animation APIs. It adds no third-party dependency, request, database migration or configuration requirement. Low-memory/low-core devices and data-saver connections skip the Canvas layer; mobile uses fewer points. Canvas rendering is capped near 30fps and pauses when the hero is offscreen or the tab is hidden. All real content is readable if scripting fails.

Files: `app/static/js/experience.js`, `app/static/css/experience.css`. The base template loads them; private admin pages are excluded at runtime. Existing admin controls and workflows are unchanged.

Validation: Python 3.13.15; six client/design regression tests; browser suite covers 28 responsive cases plus normal animation mode, pause persistence, resume, live reduced-motion changes, and 320px overflow. External assets are blocked in browser QA to verify the local fallback. No live Render or Lighthouse score is claimed.
