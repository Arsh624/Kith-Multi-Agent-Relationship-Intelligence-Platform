# Kith Design System

Locked design direction (via the design-for-ai method). Re-read before any UI change;
deviations edit this file first, then code.

## Direction

**Quiet modern.** Minimal, confident, current. Near-black warm-neutral canvas, one rose
accent, hairline structure, generous negative space. No ornament, no skeuomorphism, no AI
slop (no cyan-on-dark, no glassmorphism, no neon, no Inter). Dark by default with a real
light toggle.

- **Register:** product with portfolio-grade polish.
- **Personality words:** minimal, modern, precise.
- **Theme:** dark default, light optional, both first-class. Toggle persists per user.

## Typography

- **Display / wordmark / headings / numerals:** Space Grotesk (modern grotesk, tight).
- **Body / UI:** Hanken Grotesk. Neither is Inter/Roboto/Open Sans/Arial.
- Google Fonts. Body 15-16px, leading 1.45. Tight heading tracking. Hierarchy by weight
  and space, not boxes.

## Color (palette.mjs, seed hue 12, balanced, analogous, contrast-checked)

Warm-neutral grays + a single rose accent. Themed via `[data-theme]`.

Dark (default): bg #131212, surface #1a1919, surface-2 #242122, border #2d2929,
text #ece6e7, dim #beb5b5, faint #978889. Accent #e2546f, hover #f36b82.
Light: bg #fdfcfc, surface #faf8f8, surface-2 #f3eff0, border #ece6e7,
text #312d2d, dim #696161. Accent #e2546f, hover #c9455f.

Graph nodes: you = accent #e2546f, person = #5fb98e (soft green), company = #6f86c9
(muted indigo). Functional: error #e1524f, success #5ad664, warning #dbb155.

## Style rules

- **Flat and crisp, not tactile.** Elevation by a slightly lighter surface and a 1px
  hairline border, not heavy shadows or bevels. Subtle shadow only on floating panels.
- Primary button: solid accent. Secondary: surface + hairline. Hover lightens; active
  nudges 1px. Focus: 2px accent ring.
- Inputs: surface fill, hairline border, accent focus ring. No inner-shadow skeuomorphism.
- Rounded corners 10-12px. Tabs are a minimal underline (active = accent underline), not
  folders.
- Spacing varied: tight within groups, generous between. Left-aligned.

## Layout rules

- Two tabs renamed: **Today** (tasks) and **Network** (graph).
- Header carries the wordmark, a theme toggle, and Log out.
- Map toolbar declutter stays: primary Add-person + Search visible; Import/Sync/Reindex/
  Find-paths behind a Tools menu; Delete is a small accent/red icon.
- Graph nodes show the name with the role on a second line in the accent color (parens),
  so role is readable at a glance. Canvas + label colors follow the active theme.
