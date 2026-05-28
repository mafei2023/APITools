# Design

## Theme

Auto-switch: light mode by default, dark mode via `prefers-color-scheme: dark` media query.

Scene: developer daytime on a bright screen wants clear contrast; same developer at 2am in a dim room wants reduced luminance without losing readability. Both are first-class.

## Color

Strategy: **Restrained** — tinted neutrals + one accent ≤10%.

OKLCH color system. All neutrals tinted toward the accent hue (chroma 0.005–0.01) to avoid dead grays.

### Light mode

| Role | OKLCH | Usage |
|------|-------|-------|
| Surface | `oklch(0.985 0.004 250)` | Page background |
| Surface-raised | `oklch(0.96 0.005 250)` | Cards, sections |
| Surface-sunken | `oklch(0.94 0.005 250)` | Input fields, code blocks |
| Border | `oklch(0.88 0.006 250)` | Subtle dividers |
| Text-primary | `oklch(0.18 0.008 250)` | Headings, key text |
| Text-secondary | `oklch(0.45 0.008 250)` | Labels, hints |
| Text-tertiary | `oklch(0.6 0.006 250)` | Placeholders, timestamps |
| Accent | `oklch(0.55 0.14 250)` | Primary actions, active states |
| Accent-hover | `oklch(0.48 0.15 250)` | Hover states |
| Success | `oklch(0.65 0.17 155)` | Key available |
| Danger | `oklch(0.55 0.18 25)` | Key failed, destructive actions |
| Warning | `oklch(0.7 0.15 80)` | Testing in progress |

### Dark mode

| Role | OKLCH | Usage |
|------|-------|-------|
| Surface | `oklch(0.14 0.006 250)` | Page background |
| Surface-raised | `oklch(0.18 0.007 250)` | Cards, sections |
| Surface-sunken | `oklch(0.11 0.005 250)` | Input fields, code blocks |
| Border | `oklch(0.26 0.008 250)` | Subtle dividers |
| Text-primary | `oklch(0.92 0.004 250)` | Headings, key text |
| Text-secondary | `oklch(0.6 0.006 250)` | Labels, hints |
| Text-tertiary | `oklch(0.42 0.005 250)` | Placeholders, timestamps |
| Accent | `oklch(0.65 0.14 250)` | Primary actions, active states |
| Accent-hover | `oklch(0.72 0.13 250)` | Hover states |
| Success | `oklch(0.7 0.16 155)` | Key available |
| Danger | `oklch(0.6 0.18 25)` | Key failed, destructive actions |
| Warning | `oklch(0.75 0.14 80)` | Testing in progress |

Accent hue 250 = a cool, slightly blue-shifted cyan. Not the generic SaaS blue (230), not the crypto neon (190). Clean, technical, calm.

## Typography

- **UI text**: system sans-serif stack: `-apple-system, "Segoe UI", "Microsoft YaHei", sans-serif`
- **Code / keys / data**: monospace stack: `"Cascadia Code", "Fira Code", "JetBrains Mono", "Cascadia Mono", monospace`
- Body size: 13px (tool UI, not marketing)
- Line height: 1.5 for prose, 1.4 for UI labels
- Max line length: 65ch (for any prose sections, rare in this tool)

### Scale

| Level | Size | Weight | Use |
|-------|------|--------|-----|
| Page title | 18px | 600 | Top-level heading |
| Section title | 12px | 600 | Uppercase, letter-spacing 0.5px |
| Body | 13px | 400 | Default text |
| Label | 12px | 500 | Form labels, stat labels |
| Code | 12px | 400 | Keys, code blocks, values |
| Micro | 11px | 400 | Tags, latency, timestamps |

## Spacing

Base unit: 4px. Scale: 4, 8, 12, 16, 20, 24, 32, 40.

- Component padding: 16–20px
- Between sections: 16px
- Between related items: 8px
- Tight groupings (inline elements): 4–6px

No uniform padding everywhere. Inputs get 10px vertical, 12px horizontal. Buttons get 9px vertical, 18px horizontal.

## Radius

- Small elements (buttons, tags, inputs): 6px
- Medium elements (cards, sections): 8px
- Large elements (modals): 12px
- Circular (status dots): 50%

## Elevation

No box shadows for depth. Use border color and surface color differentiation only. One exception: modal overlay uses `rgba(0,0,0,0.6)` backdrop.

## Components

### Key list item

Horizontal layout: status dot (8px circle) → group tag (optional) → key text (monospace, truncated) → latency → error text → test button → delete button. All inline, no wrapping. Background: surface-sunken, 1px border.

### Status indicators

Three states, always accompanied by text label (not color-only):
- **Available**: green dot + "可用"
- **Failed**: red dot + error message
- **Testing**: amber dot, pulsing animation (opacity 1→0.3, 1s infinite)

### Tabs

Group tabs: surface-sunken background, 1px border. Active: accent fill, no border. Virtual tabs (全部, 统计): slightly different background to distinguish from real groups.

### Buttons

- Primary: accent background, white text
- Secondary: surface-raised background, 1px border
- Danger: red background, white text
- Copy: green background, white text

All: 7px radius, no border-radius on text-only inline buttons.

### Toast

Fixed bottom-center. Surface-raised background, 1px border. 2-second auto-dismiss. No icon, just text.

### Modal

Centered overlay. Surface-raised background, 12px radius, 24px padding. Max-width 400px. No close icon — "取消" button handles dismissal.

## Motion

Minimal. Only two animations:

1. **Testing pulse**: `opacity: 1 → 0.3`, 1s, ease-in-out, infinite. On status dot during test.
2. **Toast fade**: `opacity: 0 → 1`, 300ms, ease-out. On show.

No layout transitions. No hover transforms. State changes are instant.
