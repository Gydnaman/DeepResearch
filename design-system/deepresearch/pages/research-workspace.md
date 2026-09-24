# Workspace Page Override

This page-specific layer refines design-system/deepresearch/MASTER.md for the research workspace. All unlisted colors, state semantics, motion, focus, and responsive checks continue to inherit from MASTER.md.

## Page Pattern

Use an operational research workspace, not a landing page: compact top bar, persistent navigation, active run summary, chronological event stream, and evidence/report panes. Keep the next meaningful action visible. Do not add personalization, testimonials, conversion funnels, or a large marketing hero.

## Typography Override

Chinese research prose and navigation use a system sans stack: Inter, Segoe UI, Microsoft YaHei, sans-serif. Use Fira Code only for IDs, event sequence values, and technical metadata. Do not load remote fonts. This override keeps Chinese body text readable and keeps the app available offline.

## Layout Override

- Desktop: narrow navigation, central timeline, contextual evidence/report panel.
- Tablet: timeline first, evidence panel below or in a collapsible section.
- 375px: single column; no fixed-width data table or horizontal scrolling.
- Use 8/12/16/24px gaps and dense rows with enough line-height for scanning.

## Interaction Override

- Each state includes text and icon in addition to color.
- Event rows are ordered by persistent sequence; connection recovery is visible.
- Citation controls are keyboard reachable and take the reader to its Evidence item.
- Loading, empty, failed, disabled, cancelled, and fixture states remain explicit.

## Anti-Patterns

No landing-page hero, fictional social proof, animated chart, hover-only action, color-only status, or external font dependency.
