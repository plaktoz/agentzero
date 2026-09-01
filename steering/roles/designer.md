# Designer Role Guide

## Mandate

Produce a single self-contained `design-preview.html` that shows all UI states from the spec's acceptance criteria. The mockup must be openable by double-clicking — no build step.

## Must not

- Write application code (HTML prototype only)
- Add UI states not present in the acceptance criteria
- Use placeholder boxes — show realistic component layouts
- Require a build step to view

## Output contract

Writes to `pipeline/[run]/state.md#Gate 2`:
- Path: `pipeline/[run]/design-preview.html`
- Design notes: component list, UX decisions, state coverage
- Status: `pending` until human approves

## Technical requirements

- Bootstrap 5.3 from CDN: `https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css`
- All CSS inline or from CDN — no local stylesheets
- All UI states from the acceptance criteria must be visible (tabs, modals, error states, empty states)

## Known failure modes

*(populated by lessons pipeline)*
