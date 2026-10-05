# UI_SPEC.md — Human-Looking Industrial UI Direction

## Design goal

The UI should look like a real internal drilling-operations product that has been refined over time.

It must not look like an AI-generated SaaS dashboard.

Think:
- engineering workstation
- compact command-centre software
- deliberate information hierarchy
- high-density but readable
- neutral and serious
- interaction over decoration

---

# Screen target

Design first for:

```text
1440 × 900
```

Also verify:

```text
1366 × 768
```

No mobile work in P0.

---

# Layout

## Side rail

Width:
- 64 px collapsed/fixed

Contains icons + short labels for:
- Live
- Wells
- Knowledge
- Documents

Do not add 10 navigation items.

## Top bar

Height:
- 56 px

Contains:
- NWIS wordmark
- active well
- `LIVE REPLAY` status
- replay controls
- backend/provider status
- compact `DEMO DATA` badge

## Main live grid

At 1440 px:

```text
┌──────────────────────────────────────────────────────────────┐
│  Context strip                                               │
├──────────────────────────────┬───────────────────────────────┤
│                              │                               │
│       Offset well map        │       Hazard horizon          │
│                              │                               │
│                              │                               │
├──────────────────────────────┴───────────────────────────────┤
│  Telemetry strip                                             │
└──────────────────────────────────────────────────────────────┘
```

Recommended:
- map: ~58% of main width
- horizon: ~42%
- map/horizon height: ~500 px at 900 px viewport
- telemetry: 170–190 px

Evidence and copilot use overlays/drawers rather than permanently shrinking the workspace.

---

# Visual language

## Backgrounds

Use four levels only.

Example tokens:

```text
--bg-0: #0B0F12
--bg-1: #11171B
--bg-2: #171E23
--bg-3: #1E272D
```

Borders:

```text
--border-subtle: rgba(255,255,255,0.08)
--border-strong: rgba(255,255,255,0.14)
```

Text:

```text
--text-primary: #E8EEF1
--text-secondary: #A8B3B9
--text-muted: #727F86
```

Semantic colors:

```text
--live: #38B2A3
--watch: #D8A84E
--elevated: #D6635D
--info: #6D9BC5
```

Do not use large solid red/amber panels.

Use semantic color in:
- 2–3 px accent line
- icon
- state badge
- small marker
- chart reference region

---

# Typography

Use:
- Inter, Geist, or IBM Plex Sans for UI
- IBM Plex Mono / Geist Mono for telemetry numbers

Hierarchy:

```text
Page/feature title   18–20 px / 600
Section title        13–14 px / 600
Body                 13 px / 400
Metadata             11–12 px / 500
Telemetry major      18–24 px / mono / 500
Axis labels          10–11 px
```

Avoid 32–48 px dashboard text.

---

# Shape

Corner radius:
- main panels: 8 px
- controls: 6 px
- tags: 4 px

Do not use 16–24 px rounded SaaS cards.

Shadow:
- almost none
- rely on background contrast and borders

---

# Live context strip

This should feel like an instrument strip, not six cards.

Example:

```text
NWIS-ACT-01
MD 3,284.6 m  |  BARAIL  |  ROP 18.2 m/h  |  TORQUE 14.8 kN·m
FLOW Δ -21 L/min  |  LOOK-AHEAD WATCH 96 m
```

Use separators and alignment rather than separate boxes.

---

# Map

## Active well

Marker:
- diamond or concentric-ring marker
- live teal
- small pulsing outer ring allowed only during replay

## Offset wells

Marker:
- circular
- neutral when no relevant hazard
- subtle amber/red ring when relevant historical incident exists

Marker tooltip:
- well name
- distance
- relevant events
- formation match

## Radius

Render a thin dashed circle.

Radius control:
- 2 km / 5 km / 10 km segmented control
- compact, top-left over map

## Interaction

Click:
- selected marker gets a stronger outline
- map performs a short fly-to
- right-side well drawer opens

No bouncing pins.

---

# Hazard Horizon

This is the hero visualization.

Vertical depth increases downward.

Required:
- current bit marker
- current depth label
- shaded look-ahead band
- formation bands
- historical projected event marks
- upcoming alert callout

Formation bands:
- muted, desaturated fills
- labels aligned on the right edge

Current bit:
- crisp horizontal line
- small triangular bit marker
- numeric depth

Look-ahead:
- translucent bracket from current bit to +150 m
- do not use a giant colored block

Historical incidents:
- short line marker + compact icon
- stacked slightly if overlapping

Example callout:

```text
MUD LOSS
72 m ahead
3 historical analogs
Evidence 74
```

`Evidence 74` must have a tooltip explaining the score.

---

# Telemetry

Do not draw eight full charts.

Use four compact charts:

1. ROP
2. Torque
3. Standpipe pressure
4. Flow delta / pit trend

Each chart:
- 120-sample window
- no chart legend if title makes it obvious
- subtle grid
- right-aligned current value
- shared time direction

During alert formation:
- add a subtle vertical/current-state reference line

---

# Drawers

## Evidence drawer

Width:
- 460–520 px

Sections:
1. alert summary
2. score breakdown
3. current live signals
4. supporting analog events
5. source evidence

Avoid card-inside-card-inside-card.

Use horizontal separators.

## Copilot drawer

Width:
- 420–480 px

Closed by default.

Top:
`Ask institutional memory`

Suggested prompts:
- What happened in this formation ahead?
- Which offset wells support this alert?
- What response was recorded historically?

Chat bubbles should be minimal.
Citations should look like engineering source references, not web-search chips.

---

# Documents screen

Left:
- upload area
- document table

Right:
- selected document / extraction results

Upload box should not consume half the page.

Progress looks like a processing pipeline:

```text
READ  ✓
OCR   SKIPPED
EXTRACT ✓
VERIFY ✓
INDEX ✓
```

When events are extracted, show compact table rows, not giant cards.

---

# Knowledge screen

Top:
- search input
- three filter controls

Main:
- event table

Columns:
- Event
- Well
- Formation
- Depth
- Severity
- Source

Click row:
- opens evidence drawer

The copilot is not the main search UI.

---

# Interaction design

Use motion only for:
- map fly-to
- bit movement
- look-ahead state transition
- drawer open/close
- source highlight

Duration:
- 160–240 ms for UI
- interpolate live bit movement over 700–900 ms between telemetry samples

No looping decorative animation.

---

# Human-looking details

These small decisions matter:

- state badges have consistent short labels
- timestamps and units align
- rows use tabular numerals
- empty areas are not filled with pointless cards
- real spacing irregularity follows content needs instead of a rigid dashboard template
- labels are specific: `Historical response observed`, not `AI Recommendation`
- source references show document name + page
- warning copy is short
- tooltips explain uncommon technical concepts
- visual density is higher than a consumer app
- every visible control has an actual function

---

# Forbidden aesthetic patterns

Do not use:
- glowing neon borders
- purple/blue AI gradients
- glass panes
- fake 3D oil rigs
- huge circular gauges
- rounded KPI card grids
- animated particle backgrounds
- sparkle icons
- robot/brain imagery
- excessive badges
- emojis
- generated stock illustrations

---

# Final visual checkpoint

Before demo freeze, ask:

1. Is the Hazard Horizon visually dominant enough?
2. Does the map feel genuinely interactive?
3. Can I trace an alert to evidence in two clicks?
4. Does the UI look credible at 100% browser zoom?
5. Is any surface decorative rather than useful?
6. Is the copilot appropriately secondary?
7. Are we hiding weaknesses behind visual effects?

If yes to question 7, simplify.
