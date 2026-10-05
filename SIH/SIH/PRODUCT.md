# PRODUCT.md — NWIS Evidence-Backed Look-Ahead Intelligence

## Product definition

NWIS is a standalone drilling decision-support layer designed to sit alongside Oil India's eRTMAC workflow.

It turns historical drilling reports and well records into a structured, searchable institutional memory, then continuously contextualizes one active well against nearby and geologically analogous offset wells.

Its signature capability is the **Formation-Aware Look-Ahead Hazard Horizon**. As simulated eRTMAC telemetry advances the active bit, NWIS projects historical incidents from equivalent positions in the same formation onto the active well and surfaces hazards before the bit reaches the analogous interval.

The product must be **evidence first**. Every important event, alert, and copilot claim should be traceable to a source document and page.

NWIS does not autonomously control drilling equipment and does not present AI-generated instructions as authoritative drilling actions.

### Prototype promise

The demo must prove this complete chain:

**historical report → structured drilling event → offset-well intelligence → live drilling context → proactive alert → exact evidence → AI-supported decision context**

---

## Target users

Primary:
- Drilling engineer monitoring an active well
- eRTMAC command-centre engineer

Secondary:
- Drilling superintendent
- Well planning engineer
- Drilling optimization engineer
- Office-based specialist reviewing offset-well history

The UI should assume technically literate users who value dense, compact, evidence-rich information.

---

## Problem being solved

eRTMAC can show what the active well is doing now, but engineers still need to know what happened in relevant historical wells.

That knowledge is fragmented across:
- Well Completion Reports
- Daily Drilling Reports
- mud logging records
- drilling databases
- operational event records
- individual experience

NWIS should reduce the time required to answer:

1. Which nearby or analogous wells matter right now?
2. What happened when those wells crossed this formation?
3. Is a historically recurring hazard ahead of the bit?
4. Does current telemetry show supporting warning signs?
5. What historical evidence supports the alert?
6. What response was recorded historically?

---

# Core user journey

## 1. Open the live intelligence workspace

The user lands directly on the active-well workspace.

Visible immediately:
- active well name
- measured depth
- current formation
- ROP
- torque
- flow balance
- current look-ahead status
- map of the active well and 5–8 offsets
- formation-aware hazard horizon

The user should understand the situation within 10 seconds.

## 2. Explore nearby wells

The user clicks an offset well on the map.

A compact drawer shows:
- distance from active well
- formations intersected
- historical event count
- analog relevance
- relevant hazards

The user selects an event and sees:
- event type
- historical depth interval
- formation
- severity
- concise description
- historical response observed
- source document
- exact page
- evidence excerpt
- extraction confidence

## 3. Ingest a historical report

The user opens `Documents`.

They upload a PDF.

The system:
1. validates the file
2. extracts text page by page
3. uses AI vision/OCR only where a page has insufficient machine-readable text
4. extracts structured drilling events
5. validates the model output
6. stores source-page evidence
7. creates embeddings for retrieval
8. makes the new event available to search and look-ahead logic

The UI shows staged progress:
- Reading document
- Recovering scanned pages
- Extracting drilling events
- Validating evidence
- Indexing knowledge
- Completed

## 4. Start simulated eRTMAC replay

The user clicks `Start replay`.

Telemetry advances at one sample per second.

The UI updates:
- current bit depth
- formation position
- telemetry charts
- current look-ahead hazards

As the bit approaches an analogous historical incident interval, the hazard state changes:

`Clear → Watch → Elevated`

## 5. Explain the proactive alert

The user clicks `Why this alert?`

The evidence drawer shows:
- hazard type
- look-ahead distance
- evidence score
- supporting wells
- equivalent historical depths
- recurrence across wells
- current telemetry signals
- exact source evidence

Important wording:

> Evidence score reflects historical similarity, recurrence, evidence quality, and live corroboration. It is not a calibrated probability of occurrence.

## 6. Ask the grounded copilot

Example question:

> What happened in nearby wells in the Barail interval ahead of us?

The copilot:
- retrieves only relevant indexed evidence
- answers concisely
- cites every substantive claim
- labels mitigation content as `Historical response observed`
- says when evidence is insufficient

The copilot is secondary to the live intelligence workspace, not the product's main screen.

---

# P0 — Must work for the final demo

## P0.1 Live workspace

- One active well
- Six offset wells
- User-selectable radius
- Interactive MapLibre map
- Current well and formation context
- Synthetic/public-demo-data disclosure

Acceptance:
- live page is understandable without narration
- map interaction is reliable

## P0.2 Formation-aware Look-Ahead Hazard Horizon

- 2–4 formations
- current bit marker
- 150 m default look-ahead window
- historical incidents projected by normalized position within matching formation
- three event types:
  - mud loss / lost circulation
  - stuck pipe
  - kick / influx
- Clear / Watch / Elevated states

Acceptance:
- replay produces a real backend-calculated alert before the bit reaches the projected incident depth

## P0.3 Simulated eRTMAC stream

Controls:
- Start
- Pause
- Resume
- Reset

Data:
- depth
- ROP
- WOB
- RPM
- torque
- standpipe pressure
- flow in
- flow out
- pit volume
- gas units

Transport:
- WebSocket preferred
- REST polling fallback

Acceptance:
- reset always returns to the exact scripted state
- no random values in the main demo

## P0.4 Evidence-backed alert explanation

Each alert shows:
- hazard
- look-ahead metres
- evidence score
- supporting well count
- score decomposition
- contributing live signals
- supporting historical events
- source document/page
- historical response observed

Acceptance:
- no alert can exist without stored evidence

## P0.5 Functional report ingestion

- PDF upload
- 20 MB maximum
- PyMuPDF page extraction
- vision/OCR fallback for low-text pages
- strict structured AI extraction
- source-page preservation
- evidence verification
- embeddings/indexing

Acceptance:
- supplied demo report produces at least one correct structured event with page evidence

## P0.6 Searchable institutional memory

Filters:
- well
- formation
- hazard type
- free-text search

Results:
- structured event
- source
- page
- evidence preview

Acceptance:
- known demo event can be found in under three interactions

## P0.7 Grounded copilot

- retrieves evidence before answering
- answers from retrieved evidence only
- clickable citations
- current formation/well context may be inherited from live workspace
- explicit insufficient-evidence behavior
- provider-failure fallback to raw evidence results

Acceptance:
- scripted demo question returns a cited answer
- unsupported question does not hallucinate

## P0.8 Demo hardening

- loading states
- empty states
- provider error states
- map-tile fallback
- AI-unavailable fallback
- WebSocket fallback
- one-click demo reset
- no dead navigation
- no broken console errors in demo path

---

# P1 — Only after the full P0 loop works

- Side-by-side offset-well comparison aligned by formation
- Editable AI extraction review
- Alert history timeline
- Batch document ingestion
- additional replay scenarios for stuck pipe and kick
- small analytics summary
- hybrid lexical + vector retrieval
- optional unsupervised telemetry anomaly score using a deterministic IsolationForest trained on seeded normal telemetry
- optional real Volve WITSML parser for one well
- printable/exportable evidence brief
- Supabase hosted persistence if not already used

---

# P2 — Do not spend hackathon time here

- direct eRTMAC integration
- full WITSML/ETP production connector
- Kafka
- Redis/Celery
- microservices
- graph database
- enterprise SSO/RBAC
- multi-rig fleet monitoring
- calibrated supervised hazard-prediction model
- deep-learning time-series forecasting
- true stratigraphic-depth correction
- full well-trajectory/minimum-curvature engine
- full geomechanics
- autonomous drilling recommendations
- OSDU production integration
- sovereign/on-prem model serving
- mobile application

---

# Non-goals

The prototype must not claim:
- synthetic incidents are real Oil India incidents
- the evidence score is a probability
- an actual OIL-labelled predictive model exists
- the copilot replaces engineering judgement
- historical mitigation is a live operating instruction
- production readiness

---

# UI expectations

The product should feel like a specialist industrial operations tool.

It should be:
- compact
- precise
- calm
- evidence-rich
- visually coherent
- interactive where interaction communicates system state

It should not look like:
- a generic SaaS template
- a chatbot with a dashboard attached
- a neon AI control room
- a page full of large rounded cards
- glassmorphism
- gradient-heavy generated UI
- a marketing landing page

The core visual hierarchy is:

1. Live context
2. Map + Hazard Horizon
3. Telemetry
4. Evidence on demand
5. Copilot as a secondary drawer

---

# Product success definition

A judge should leave the demo understanding seven things:

1. It reads historical drilling documents.
2. It structures historical incidents.
3. It identifies the nearby/analog wells that matter.
4. It understands where the active bit is within the formation.
5. It warns before an analogous historical problem interval.
6. It proves the alert with exact evidence.
7. The AI is grounded rather than free-form.
