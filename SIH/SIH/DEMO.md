# DEMO.md — Final Demo Plan

## Demo thesis

> NWIS turns historical drilling records into a formation-aware institutional memory that looks ahead of the active bit and proves every alert with source evidence.

The demo should last approximately 4–5 minutes.

Do not try to show every route.

---

# Required demo state

Active well:
- `NWIS-ACT-01`

Offset wells:
- `NWIS-OFF-01`
- `NWIS-OFF-02`
- `NWIS-OFF-03`
- `NWIS-OFF-04`
- `NWIS-OFF-05`
- `NWIS-OFF-06`

Formations:
- Tipam
- Barail
- Kopili

Hazard classes:
- Mud loss
- Stuck pipe
- Kick

Primary demo hazard:
- Mud loss in Barail

All Oil-India-like names and event values are synthetic unless the UI explicitly identifies a source as public Volve-derived material.

---

# 4–5 minute demo sequence

## 0:00–0:25 — Problem framing

Open `/live`.

Say:

> eRTMAC tells an engineer what the active well is doing now. NWIS adds what happened in relevant historical wells, where it happened inside the formation, and what evidence supports the warning.

Point to:
- active well
- offsets
- current formation
- hazard horizon

Do not begin on slides or architecture.

---

## 0:25–0:55 — Institutional memory

Click `NWIS-OFF-03`.

Show:
- distance
- Barail interval
- mud-loss event
- source evidence

Open the event.

Say:

> This is not a free-form AI memory. It is a structured drilling event linked back to the report and exact page.

Open the source page briefly.

---

## 0:55–1:25 — Show that ingestion is real

Open `Documents`.

Upload `demo_report_barail.pdf`.

Show pipeline:
- Reading
- Extracting
- Validating
- Indexing

Show extracted event.

If the API is slow:
- use the same known file hash
- backend may return a cached verified extraction in demo mode
- UI must label it `cached verified extraction`

Say:

> The same event structure driving the live system is built from historical reports.

Do not spend more than 30 seconds here.

---

## 1:25–2:30 — Wow moment: Look-Ahead Hazard Horizon

Return to `/live`.

Click `Reset`, then `Start replay`.

Narrate while depth advances:

> We are now replaying a simulated eRTMAC stream. The live values are synthetic, but the alert logic is actually running.

As bit enters Barail:
- Watch state appears

As corroborating telemetry rises:
- Elevated state appears

Say:

> NWIS has not matched raw depths. It aligned equivalent positions inside the same formation, found recurring mud-loss incidents in nearby offsets, and combined that historical evidence with current flow and pit-volume behavior.

Pause replay immediately after the elevated alert appears.

---

## 2:30–3:20 — Explainability

Click `Why this alert?`

Show:
- 70–90 m look-ahead
- evidence score
- three supporting wells
- score decomposition
- flow imbalance
- pit-volume trend

Then click one analog.

Show:
- historical depth
- projected active depth
- report/page evidence

Say:

> The score is deliberately not presented as a probability. With no labelled OIL training set, we prefer an auditable evidence score to a fake confidence number.

This answer is important in Q&A as well.

---

## 3:20–4:05 — Grounded AI

Open copilot.

Ask:

> What happened in nearby wells in the Barail interval ahead of us?

Expected response:
- concise summary of recurring mud loss
- supporting offset wells
- historical response observed
- 2–3 citations

Click one citation.

Say:

> The copilot can synthesize the institutional memory, but it cannot silently invent the evidence.

---

## 4:05–4:35 — Production path

Close drawer and return to the live screen.

Say:

> In production, the simulator is replaced by eRTMAC through a WITSML/ETP or OIL-specific adapter, the curated reports become OIL's full corpus, and the explainable evidence layer can be augmented by a calibrated predictive model trained on labelled OIL events.

Stop.

Do not demo settings or unfinished P1 features.

---

# Features not required in the live demo

- auth
- RBAC
- user management
- multi-rig screen
- exports
- batch ingestion
- all three hazard replay scenarios
- mobile
- WITSML live connector
- IsolationForest
- production model

They can be described during Q&A.

---

# Demo safety net

Prepare:

1. hosted app
2. local Docker app
3. local SQLite fallback
4. five screenshots:
   - live baseline
   - Watch
   - Elevated
   - evidence drawer
   - copilot with citations
5. 45–60 second screen recording of the complete wow moment
6. cached verified extraction for the known demo PDF
7. one `Reset demo` action

---

# Judging-criteria mapping

Exact grand-finale rubrics can vary by event/college, so the mapping uses the SIH criteria that recur across published guidance: novelty, problem understanding, feasibility, impact/usefulness, UX/execution, scalability/future progression, and presentation.

## Problem understanding

Prove:
- eRTMAC already handles live monitoring
- the missing capability is historical context and institutional memory
- raw depth comparison is insufficient
- historical evidence is fragmented

Visible proof:
- eRTMAC-like replay is only one input
- formation alignment and reports are central

## Innovation / originality

Lead with:
- Formation-Aware Look-Ahead Hazard Horizon
- projected incidents inside equivalent formations
- alert-to-source traceability
- grounded copilot as a supporting layer, not the novelty itself

Do not pitch:
- "we used an LLM"
- "we made a chatbot"
- "we made a map"

## Technical feasibility

Prove:
- real ingestion pipeline
- deterministic replay
- real formation projection
- real alert calculation
- real evidence links
- controlled fallbacks

Mention:
- Supabase/Postgres migration path
- WITSML/ETP production adapter path
- no unnecessary distributed infrastructure

## Impact / usefulness

Explain:
- engineers can search historical experience in seconds
- proactive context appears before the bit reaches analogous trouble
- source evidence reduces black-box trust problems
- institutional knowledge survives personnel turnover

Avoid inventing financial savings without OIL data.

## Prototype / execution quality

Prove:
- complete end-to-end flow
- polished UI
- no dead buttons
- reset works
- provider failure does not destroy the demo

## UX

Prove:
- active situation understood in 10 seconds
- alert explanation in one click
- source evidence in another click
- copilot is optional

## Scalability / future potential

Describe:
- Postgres/PostGIS
- pgvector
- WITSML/ETP
- OIL full document corpus
- calibrated supervised model
- on-prem/private deployment
- engineer feedback loop
- multi-rig support

Do not build these during the hackathon.

## Presentation

Narrative:
1. live monitoring exists
2. institutional memory is missing
3. historical event is structured
4. bit advances
5. proactive alert appears
6. evidence proves it
7. AI synthesizes it
8. production migration is clear

---

# Biggest technical risks

## 1. Alert feels hard-coded

Risk:
Judges think the wow moment is scripted UI.

Mitigation:
- backend score endpoint
- show score decomposition
- use deterministic but real telemetry computation
- allow replay pause at arbitrary points
- unit-test projection

Fallback:
- expose a small `Explain calculation` panel during Q&A

## 2. AI extraction hallucinates

Mitigation:
- strict schema
- page-level input
- exact evidence text
- validation
- one retry
- no evidence → no event

Fallback:
- cached verified extraction only for known demo file

## 3. OCR is slow/unreliable

Mitigation:
- PyMuPDF first
- OCR/vision only on low-text pages
- text-native main demo report

Fallback:
- show scan support during Q&A, not main demo

## 4. Supabase/network outage

Mitigation:
- repository abstraction
- SQLite fallback
- deterministic local seed

Fallback:
- restart with `DATA_BACKEND=sqlite`

## 5. Map service failure

Mitigation:
- MapLibre
- fallback local style
- keep geometry independent of tiles

Fallback:
- no basemap, still display wells and radius

## 6. WebSocket issue on hosting

Mitigation:
- REST polling fallback

Fallback:
- automatically show `Replay fallback`

## 7. Copilot latency/provider issue

Mitigation:
- retrieve evidence before generation
- short prompt
- concise output

Fallback:
- deterministic evidence summary

## 8. UI looks generic

Mitigation:
- `UI_SPEC.md`
- build hero screen before long backend work
- no landing page
- no giant KPI cards

Fallback:
- freeze features early and spend final 4 hours on hierarchy/spacing instead of adding functionality

## 9. Judges ask where the ML model is

Answer:

> We do not have labelled Oil India incident windows, so we did not manufacture a supervised accuracy claim. The prototype's proactive layer is an explainable predictive-analytics score over offset analogs and live corroboration. We can add an unsupervised anomaly signal now, and the production architecture is designed to replace/augment it with a calibrated model once OIL's labelled data is available.

If P1 IsolationForest exists, show it as an auxiliary signal.

## 10. Competitors show more buzzwords

Do not compete feature-for-feature.

Emphasize:
- complete working chain
- visible source evidence
- formation-relative logic
- polished operator workflow
- graceful limitations

---

# Q&A answers worth rehearsing

## Why not compare wells at the same measured depth?

Because formations occur at different absolute depths between wells. The prototype aligns the relative position inside the same formation before projecting the historical event to the active well.

## Is evidence score a probability?

No. It is a transparent ranking of historical analog relevance, recurrence, evidence quality, and live corroboration. A calibrated probability requires labelled OIL data.

## Is the demo real-time?

The data source is a deterministic replay, but the streaming, projection, scoring, retrieval, and alert logic run live.

## Why not a knowledge graph?

For 5–8 wells and a few hundred evidence chunks, it adds integration risk without improving the demo. The relational/event model already preserves the important relationships.

## How do you integrate with eRTMAC?

Use an adapter that maps eRTMAC/WITSML-like telemetry into the internal telemetry DTO. The rest of NWIS does not depend on the simulator.

## How do you prevent hallucinations?

The copilot sees retrieved evidence only, every major claim cites stored source references, and structured extraction is schema-validated with evidence text and page checks.

## Can this deploy on-prem?

Yes in the future. The application layer is independent of Supabase/Gemini-specific storage; production can move to OIL-controlled Postgres/object storage and approved local models.
