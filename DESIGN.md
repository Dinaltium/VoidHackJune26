# Design

Visual system for Agent Firewall. Source of truth: `dashboard/app/globals.css`
(OKLCH tokens). Identity to preserve: a dark, calm control-plane where saturated
color appears only to encode a decision.

## Theme

Dark, single mode. Physical scene: a security engineer at 23:00 watching a
wall-mounted control plane in a dim SOC, scanning a live feed of agent actions
for the red ones. **Color strategy: restrained** — tinted-neutral dark surfaces
+ one cool brand accent (azure), with green / amber / red reserved strictly for
the allow / flag / block decision states.

## Color (OKLCH)

| Token | Value | Role |
|---|---|---|
| `--bg` | `oklch(0.16 0.012 248)` | app background (cool near-black) |
| `--surface` | `oklch(0.2 0.014 248)` | panels |
| `--surface-2` | `oklch(0.24 0.016 248)` | inputs, chips, nested |
| `--border` | `oklch(0.32 0.018 248)` | hairlines |
| `--ink` | `oklch(0.97 0.004 248)` | primary text |
| `--muted` | `oklch(0.74 0.012 248)` | secondary text (AA on surfaces) |
| `--faint` | `oklch(0.6 0.012 248)` | meta / labels |
| `--brand` | `oklch(0.74 0.13 224)` | azure accent — chrome, focus, primary action |
| `--allow` | `oklch(0.78 0.15 152)` | green — allowed / safe |
| `--flag` | `oklch(0.82 0.14 84)` | amber — flagged / redacted |
| `--block` | `oklch(0.66 0.21 25)` | red — blocked / breach |

State tints (`--allow-tint`, `--flag-tint`, `--block-tint`) are low-alpha
versions of each hue used as row/card backgrounds. **Rule:** brand carries the
UI chrome; the three decision hues never appear except to mean their state.

## Typography

One sans family in multiple weights + one monospace, paired on a contrast axis
(humanist sans vs mono):

- **Sans:** `ui-sans-serif, system-ui, "Segoe UI", Roboto` — base 15px / 1.5.
  Weights: 400 body, 500–600 headings, 700 badges.
- **Mono:** `ui-monospace, "SF Mono", "Cascadia Code"` (`.mono`, ~0.86em) for
  technical content: rule names, hosts, receipt ids, tool-call signatures.
- Headings are tight but not cramped (`letter-spacing: -0.01 to -0.02em`).
  No external fonts (zero network, instant render).

## Components

- **Panel** — `--surface`, 1px `--border`, 12px radius, 18px pad. The base
  container; never nested.
- **Badge** — uppercase 11px/700 pill; filled with the state hue, text in a dark
  shade of that hue (allow/flag) or near-white (block).
- **Event card** — leading badge + title + detail + mono meta row; background
  tints to the decision hue (block = red tint, flag = amber tint, allow = plain).
- **Chip** — pill, outlined; deny chips outline red, allow chips outline green.
- **Switch** — firewall ON/OFF; track turns green (on) / red (off), 200ms thumb.
- **Step timeline** — vertical rail with dots; per-step tool calls shown as
  `Blocked` (red tint) / `Ran` rows with a mono call signature.
- **Verdict banner** — held (green tint) / breach (red tint), mark + headline +
  one line.
- **Stat** — small labeled tile, tabular-nums, semantic dot. Not the hero-metric
  template — compact, three across.

## Layout

- Centered app shell, `max-width: 1180px`, 28/24px padding.
- Two-column work surfaces (`1fr 320–340px`); collapse to one column under
  ~880–920px.
- Spacing rhythm in 4px steps (7/10/14/18/22). Vary it; don't uniform-pad.
- Z-index: semantic scale only (no 999/9999).

## Motion

- Entrances ease-out (`cubic-bezier(0.16, 1, 0.3, 1)`); `riseIn` (8px + fade) on
  new events / calls; list items stagger as they stream.
- Live connection dot pulses; switch + buttons have 120–200ms transitions.
- Every animation has a `prefers-reduced-motion: reduce` off-switch.
- No bounce, no elastic. Glow/tint used sparingly, only to signal state.

## Guardrails (per anti-references)

No gradient text, no glassmorphism-by-default, no side-stripe borders, no
ghost-card (1px border + wide shadow), card radius ≤ 12px, no all-caps tracked
eyebrows on every section, no wall-of-widgets density.
