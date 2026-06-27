# Product

## Register

product

## Users

Developers, startups, and platform/security teams building or operating AI
agents. Their context: an agent acts autonomously with real tools (email, HTTP,
shell, payments) and they need to govern — and prove — what it's allowed to do.
Primary jobs: watch agent decisions stream in (Live feed), and validate that a
policy actually holds under attack (Mission Control). A secondary audience is
hackathon judges and prospective adopters who meet the project through a landing
page and a demo video.

## Product Purpose

Agent Firewall is the **action-layer control plane** that sits between an AI
agent and the world and enforces policy on what the agent *does* — stripping
disallowed tool calls before they execute, redacting secrets in flight, and
signing every decision into an auditable trail. It exists because prompt
injection is unsolved and existing guardrails only check *text*. Success looks
like: an agent gets hijacked, attempts a dangerous action, and the firewall
blocks it in real time — visibly, and provably.

## Brand Personality

Sleek control-plane: confident, precise, lightly futuristic. Understated
authority — it reads like real infrastructure an operator trusts, not a toy and
not a pitch. Voice is terse and exact: short labels, no marketing fluff,
technical terms used correctly. Calm by default; decisive when it matters.

## Anti-references

- **Generic SaaS slop** — cream/lavender gradients, gradient text, the
  hero-metric template, endless identical icon-card grids. The AI-default look.
- **Busy enterprise dashboard** — Grafana/Splunk wall-of-widgets, tiny dense
  charts everywhere, clutter as a substitute for insight.
- **Playful / childish** — blobby mascots, bright primaries, comic energy; it
  undercuts a security product.
- **Flat & lifeless** — all-gray, no accent, no motion, no hierarchy.

## Design Principles

- **Show the invisible.** The whole point is to make the operating layer legible
  — every decision visible, signed, and explainable. Nothing happens off-screen.
- **Calm until it matters.** The surface is restrained dark; saturated color
  erupts only on a decision (allow / flag / block). Color *is* meaning, never
  decoration.
- **Proof over claims.** The UI demonstrates — live blocks, signed receipts,
  governed-vs-ungoverned — rather than asserting. Show, don't tell.
- **Operator-grade clarity.** Dense information, zero clutter; one primary action
  per surface; the eye always knows where the next decision will appear.
- **Precision as the aesthetic.** Tight type, exact spacing, and a strict
  semantic palette are the polish — not effects bolted on top.

## Accessibility & Inclusion

WCAG 2.1 AA. Body text ≥ 4.5:1 against its surface; state colors are always
paired with a text label and badge so color is never the sole signal (supports
color blindness). Every animation has a `prefers-reduced-motion` alternative.
Interactive controls are keyboard-reachable with a visible focus ring.
