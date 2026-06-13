# Kith Design System

Locked design direction (via the design-for-ai method). Re-read before any UI change;
deviations edit this file first, then code.

## Direction

**Warm analog desk.** Kith is a personal contact organizer, so it should feel like a
physical Rolodex / index-card box on a warm wooden desk, not a cold SaaS dashboard. This
is the deliberate antidote to the generic AI look (cyan-on-dark, flat cards, Inter) the
first version had.

- **Register:** product, but with brand-level personality (it is a portfolio piece).
- **Personality words:** warm, tactile, considered.
- **Light theme.** Parchment surfaces, ink text. We explicitly reject dark-mode-by-default.

## Typography

- **Display / wordmark / headings:** Fraunces (warm characterful serif). Not a default.
- **Body / UI:** Mulish (humanist sans). Not Inter/Roboto/Open Sans/Arial.
- Loaded from Google Fonts. Body 16px min, leading 1.4. Smart proportions, not uniform.

## Color (from palette.mjs, seed hue 34, balanced, complementary, contrast-checked)

Paper neutrals + terracotta accent + cool counter for links; functional colors as given.

- `--paper` #faf8f8 surface, `--paper-deep` #f3efef, `--ink` #312d2c text,
  `--ink-soft` #69615f secondary.
- `--accent` #e16347 (terracotta) primary actions; `--accent-press` #c85339.
- `--line` #cbc1be borders.
- Graph node colors: person `--person` #5aa469 (warm green), company `--company` #c87f43
  (tan), You `--you` #e16347 (terracotta). Edges warm grey; relationship edges dashed.
- Functional: error #e1524f, success #5ad664, warning #dbb155.
- Map canvas is a warm dark "desk" (`#241f1d` radial) so the bright nodes pop, but all
  app chrome is light paper.

## Skeuomorphic detail rules

- **Buttons are tactile:** subtle top-to-bottom gradient, 1px top highlight, soft drop
  shadow; on `:active` they press down (translateY 1px, shadow shrinks).
- **Inputs look inset:** faint inner shadow, paper fill.
- **Cards/panels:** layered, hue-shifted soft shadows (warm, never pure black) for real
  depth, not a flat 1px border. Depth hierarchy: raised controls > panels > page.
- **No AI tells:** no glassmorphism, no neon glow, no cyan-on-dark, left-aligned text,
  varied spacing (tight within groups, generous between).

## Layout rules

- Two tabs: Good Morning (tasks) and Map. Tabs look like physical file folders.
- **Map toolbar declutter:** primary actions (Add person, Search) stay visible; secondary
  tools (Import message, Sync, Reindex, Find paths) live behind a "Tools" menu; Delete is a
  small red trash icon, not a wide button.
- Graph nodes show the name plus the role in parentheses beneath, the role in a lighter
  accent color, so you know who someone is at a glance. Labels ~10% larger than before.
