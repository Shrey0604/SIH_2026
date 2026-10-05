# TASKS.md — NWIS Codex Execution Plan

## Rules for Codex

1. Read `PRODUCT.md`, `ARCHITECTURE.md`, `UI_SPEC.md`, `DEMO.md`, and `DEMO_DATA.md` before writing code.
2. Execute phases in order.
3. Do not start P1/P2 work while a P0 acceptance criterion is failing.
4. Keep `TASKS.md` checkboxes updated.
5. Prefer a working vertical slice over broad unfinished architecture.
6. Run the app and tests after every phase.
7. Do not add frameworks or services that are not justified by the docs.
8. Preserve the SQLite fallback even if Supabase is the main hosted backend.
9. Do not visually redesign the product without updating `UI_SPEC.md`.
10. Never call the evidence score a probability.

---

# Phase 0 — Bootstrap

## 0.1 Monorepo

- [x] create React + TypeScript + Vite frontend
- [x] create FastAPI backend
- [x] create root `Makefile`
- [x] create root `README.md`
- [x] create `.env.example`
- [x] create `scripts/dev.sh`
- [x] create health endpoint

Acceptance:
- frontend starts
- backend starts
- health endpoint returns 200
- lint/typecheck passes
- secrets are not committed

## 0.2 Database abstraction

- [x] define repository interfaces
- [x] create SQLite implementation first
- [x] create database initialization
- [x] create seed loader
- [x] create deterministic demo reset

Acceptance:
- deleting local DB and reseeding produces identical data
- one active well and six offsets exist
- events and evidence exist
- `/api/demo/reset` is idempotent

## 0.3 Supabase implementation

- [x] add PostgreSQL/Supabase repository implementation
- [x] create SQL migration
- [x] add pgvector extension migration
- [x] create storage adapter
- [x] add `DATA_BACKEND` switch

Acceptance:
- app boots against Supabase
- app boots against SQLite without code changes
- no service-role key reaches the frontend

## 0.4 Deterministic telemetry fixture

- [x] load `demo_data/telemetry_scenario.csv`
- [x] create replay state
- [x] implement start/pause/resume/reset service functions

Acceptance:
- sequence always starts at zero
- no main-demo randomness
- reset reproduces the same values

---

# Phase 1 — Build the visible product shell

## 1.1 App shell

- [x] implement fixed top bar
- [x] implement narrow side rail
- [x] add routes
- [x] redirect `/` to `/live`
- [x] add compact demo-data badge
- [x] add system-status indicator

Acceptance:
- no marketing landing page
- all visible P0 navigation works
- layout works at 1440×900 and 1366×768

## 1.2 Live context strip

Show:
- MD
- formation
- ROP
- torque
- flow balance
- look-ahead state

Acceptance:
- values come from backend
- numeric values use tabular/monospace styling
- no oversized KPI cards

## 1.3 Map

- [x] install MapLibre correctly
- [x] use OpenFreeMap style
- [x] plot active well
- [x] plot six offset wells
- [x] draw selected radius
- [x] selected-well interaction
- [x] compact legend
- [x] fallback style
- [x] separate local scoring offsets from map-only national context wells
- [x] add clustered India overview and active-area view controls
- [x] keep well symbols screen-sized at every zoom

Acceptance:
- clicking a well opens useful detail
- radius filter works
- map remains usable without basemap tiles

## 1.4 Static Hazard Horizon

- [x] vertical depth axis
- [x] formation intervals
- [x] bit marker
- [x] 150 m window
- [x] projected seeded event markers

Acceptance:
- the concept of "hazards ahead" is visually obvious
- formation/depth labels are readable

Checkpoint:
- stop and visually inspect before building more
- if this screen looks generic, fix it now

---

# Phase 2 — Make the look-ahead engine real

## 2.1 Formation context

- [x] current formation by MD
- [x] normalized formation position
- [x] tests

Acceptance:
- boundary behavior is tested
- output remains in `[0,1]`

## 2.2 Historical event projection

- [x] normalize event position inside offset formation
- [x] project into active-well formation
- [x] compute lookahead
- [x] filter 0–150 m
- [x] tests

Acceptance:
- demo event projection matches `DEMO_DATA.md`
- no cross-formation projection

## 2.3 Distance and analog scoring

- [x] Haversine distance
- [x] spatial score
- [x] look-ahead proximity score
- [x] evidence-quality score
- [x] analog relevance
- [x] decomposition output
- [x] tests

Acceptance:
- every displayed analog score can be explained
- no output is named probability

## 2.4 Hazard-specific telemetry scoring

Mud loss:
- [x] flow imbalance
- [x] pit-volume slope
- [x] optional pressure contribution

Kick:
- [x] reverse flow imbalance
- [x] pit-volume rise
- [x] gas rise

Stuck pipe:
- [x] torque deviation
- [x] ROP drop
- [x] WOB/pressure contribution

Acceptance:
- start of replay is low-risk
- planned mud-loss signals rise near the demo interval

## 2.5 Evidence score

- [x] top analog aggregation
- [x] recurrence
- [x] telemetry corroboration
- [x] state thresholds
- [x] no-evidence guard
- [x] tests

Acceptance:
- replay transitions through expected state
- at least one alert is raised before the projected historical incident depth
- reset clears runtime alerts

## 2.6 Live transport

- [x] WebSocket
- [x] control messages
- [x] frontend subscription
- [x] 120-sample ring buffer
- [x] REST fallback

Acceptance:
- UI updates once per second
- start/pause/resume/reset work repeatedly
- forced WebSocket failure falls back cleanly

---

# Phase 3 — Evidence chain

## 3.1 Alert drawer

Show:
- [x] hazard
- [x] look-ahead metres
- [x] evidence score
- [x] score breakdown
- [x] supporting wells
- [x] telemetry contribution
- [x] supporting events

Acceptance:
- `Why this alert?` works in one click
- no unexplained number is shown

## 3.2 Event evidence cards

Each card:
- [x] well
- [x] formation
- [x] depth
- [x] severity
- [x] description
- [x] historical response observed
- [x] source document
- [x] page
- [x] evidence excerpt

Acceptance:
- every demo event has at least one citation

## 3.3 Source viewer

- [x] cited-page rendering
- [x] page number
- [x] evidence excerpt
- [x] missing-highlight-safe source navigation

Acceptance:
- evidence click opens correct source page
- missing highlight does not break source navigation

---

# Phase 4 — Functional ingestion

## 4.1 Upload

- [x] PDF only
- [x] 20 MB max
- [x] SHA-256
- [x] persistent storage
- [x] ingestion job

Acceptance:
- wrong type and oversize return useful 4xx errors
- valid document creates job

## 4.2 Page extraction

- [x] PyMuPDF per page
- [x] text quality heuristic
- [x] page metadata persistence

Acceptance:
- text-native demo report is extracted correctly

## 4.3 Vision/OCR fallback

- [x] render low-text page to image
- [x] multimodal model recovery path
- [x] explicit error if provider unavailable

Acceptance:
- this path is covered by one test fixture
- main demo is not dependent on it unless rehearsed

## 4.4 Structured event extraction

- [x] Gemini structured-output client behind `AIProvider`
- [x] strict Pydantic schema
- [x] extraction prompt
- [x] validation
- [x] one retry
- [x] evidence-text verification

Acceptance:
- demo report yields expected event
- invalid response cannot create DB records
- page number is preserved

## 4.5 Chunking and embeddings

- [x] page-aware chunks
- [x] embedding service
- [x] pgvector persistence
- [x] SQLite JSON persistence
- [x] similarity query
- [x] hash cache
- [x] provider/model/dimension metadata
- [x] incompatible-vector invalidation and rebuild path

Acceptance:
- successfully ingested document becomes searchable
- unchanged file is not re-embedded unnecessarily

## 4.6 Documents UI

- [x] drop zone
- [x] staged progress
- [x] success result
- [x] failure state
- [x] evidence link

Acceptance:
- upload-to-event flow can be demonstrated without devtools

## 4.7 Gemini provider migration (pre-Phase 5)

- [x] central `AIProvider` contract
- [x] Gemini structured extraction with strict schema
- [x] Gemini low-text-page multimodal recovery
- [x] Gemini document/query embeddings at configurable dimension
- [x] grounded answer generation with supplied-source enforcement
- [x] hash-locked known-demo fallback clearly labelled in job and event records
- [x] unknown-file provider failure creates no event
- [x] mocked provider, validation, OCR, embedding, migration, and fallback tests
- [x] optional live integration verification script
- [x] live modified-PDF extraction, vector search, and grounded-answer verification

Acceptance:
- active runtime has no OpenAI dependency
- live verification bypasses the known-file cache
- existing Phase 1–4 behavior and frontend build remain unchanged

---

# Phase 5 — Knowledge and grounded copilot

## 5.1 Knowledge search

- [x] query
- [x] well filter
- [x] formation filter
- [x] hazard filter
- [x] source preview

Acceptance:
- known Barail mud-loss event is found in under three interactions

## 5.2 Retrieval

- [x] query embedding
- [x] metadata filter
- [x] vector ranking
- [x] optional lexical bonus
- [x] top-six evidence bundle

Acceptance:
- scripted question retrieves expected sources

## 5.3 Copilot backend

- [x] evidence-only prompt
- [x] live context included
- [x] citations
- [x] insufficient-evidence response
- [x] provider-failure fallback

Acceptance:
- scripted question returns at least two clickable sources
- unsupported question states evidence is insufficient
- Gemini outage still returns retrieved evidence

## 5.4 Copilot UI

- [x] right-side drawer
- [x] suggested questions
- [x] citation chips
- [x] citation opens evidence/source

Acceptance:
- copilot is closed by default
- it never visually dominates the live screen

---

# Phase 6 — Optional P1 ML signal

Do this only after P0 passes.

- [ ] create normal baseline telemetry fixture
- [ ] train IsolationForest with fixed seed
- [ ] expose anomaly score
- [ ] add it as a small auxiliary telemetry contribution
- [ ] label correctly

Acceptance:
- deterministic across restarts
- does not change the core alert explanation unexpectedly
- never called a hazard probability

---

# Phase 7 — UI polish

## 7.1 Apply `UI_SPEC.md`

- [x] typography
- [x] spacing
- [x] surface hierarchy
- [x] semantic states
- [x] table density
- [x] icon consistency
- [x] skeletons
- [x] empty states

Acceptance:
- no giant cards
- no gradient hero
- no glass effects
- no emoji icons
- corner radii are consistent
- dark UI remains readable

## 7.2 Motion

- [x] bit-marker interpolation
- [x] alert-state transition
- [x] drawer transition
- [x] map fly-to
- [x] Escape closes overlays

Acceptance:
- all motion communicates state
- animations never block interaction

---

# Phase 8 — Demo hardening

## Automated backend tests

Minimum:
- [x] formation lookup
- [x] relative position
- [x] event projection
- [x] Haversine
- [x] analog score
- [x] evidence score
- [x] no-evidence-no-alert
- [x] upload validation
- [x] expected retrieval result
- [x] reset determinism

## Frontend checks

- [x] typecheck
- [x] lint
- [x] live render
- [x] reset
- [x] alert drawer
- [x] source viewer
- [x] provider-error state

## Five-run smoke test

Repeat five times:

1. reset
2. open `/live`
3. select `NWIS-OFF-03`
4. start replay
5. reach Watch
6. reach Elevated
7. open explanation
8. open evidence
9. ask scripted copilot question
10. reset

Acceptance:
- [x] 5/5 clean
- [x] no DB repair
- [x] no reload needed

## Failure smoke test

Force:
- [x] Gemini unavailable
- [x] map style invalid
- [x] WebSocket unavailable
- [x] Supabase unavailable

Acceptance:
- [x] local fallback demo still works
- [x] each failure is visible and controlled

---

# Phase 9 — Deployment

## Single container

- [ ] build frontend
- [ ] copy frontend into backend static assets
- [ ] serve one port
- [ ] include local fallback seed
- [ ] writable data directory

Acceptance:
- `docker build` succeeds
- application loads at one URL

## Hosted demo

- [ ] configure Supabase
- [ ] configure API key
- [ ] verify WebSocket
- [ ] verify map
- [ ] verify upload
- [ ] verify reset
- [ ] verify SQLite fallback before the event

Acceptance:
- hosted and local paths both pass the smoke test

---

# 36-hour execution plan

## Hour 0–2
Freeze scope, bootstrap repo, create seed, verify Gemini extraction call.

Exit:
- both apps boot

## Hour 2–7
Build shell, map, horizon, seeded live page.

Exit:
- screenshot already looks credible

## Hour 7–13
Build replay, formation projection, analog logic, evidence score, live charts.

Exit:
- proactive alert genuinely works

## Hour 13–18
Build alert explanation and exact evidence navigation.

Exit:
- alert → source is complete

## Hour 18–23
Build upload and report intelligence.

Exit:
- one PDF creates a real structured event

## Hour 23–27
Build search and copilot.

Exit:
- scripted RAG question works

## Hour 27–31
UI polish and controlled failure states.

Exit:
- UI matches `UI_SPEC.md`

## Hour 31–34
Supabase/hosting, Docker, integration.

Exit:
- public and local demo work

## Hour 34–36
Feature freeze.

Only:
- bugs
- five rehearsals
- screen recording backup
- screenshots
- Q&A prep

No new features.

---

# Suggested six-person ownership

A — app shell + map  
B — horizon + telemetry charts  
C — backend data + replay + risk engine  
D — ingestion + AI + retrieval  
E — evidence/source viewer + knowledge UI  
F — demo data + QA + deployment + pitch integration

Critical-path work should be paired rather than isolated.

---

# Implementation notes / changelog

- 2026-10-03 — Reproduced and fixed the disappearing map wells in Firefox: adding the boundary source made `isStyleLoaded()` false and skipped subsequent well/radius sources. Overlay installation now follows `style.load` readiness, including fallback style changes. Interactive local markers use a MapLibre-owned absolute anchor with a separate fixed-pixel button, so CSS no longer offsets their geographic positions or overwrites the active diamond rotation. Zoom styling lives on the map container and survives React updates. Added `scripts/verify_map_browser.py`; verified 7 operational markers, all 24 context wells in 6 national clusters, zooms 11/8/5/2/0 with under 2 px positioning error, radius filtering, well selection, and numbered clusters after basemap failure. All 50 backend tests and frontend lint/typecheck/build passed; existing bundle-size warning remains.
- 2026-09-30 — Phase 3: added one-click alert explanation, supporting-event cards, stored synthetic source PDFs, and exact stored-page rendering shared by the live and well drawers.
- 2026-09-30 — Phase 4: added PDF validation/storage, observable ingestion jobs, PyMuPDF page extraction, low-text vision recovery, strict Responses/Pydantic extraction with one validation retry, exact evidence verification, page-aware chunking, embeddings, SQLite/pgvector persistence, hash caching, and the Documents workspace.
- 2026-09-30 — The known text-native demo PDF was ingested as 3 pages, 3 searchable chunks, and 1 page-2 MUD_LOSS event. The configured OpenAI project returned `credit_balance_exhausted`, so this run used the explicitly labelled, hash-locked verified demo cache; arbitrary reports retain an explicit provider-error state and never receive fabricated events.
- 2026-09-30 — Pre-Phase-5 provider migration: replaced the active OpenAI path with a single `GeminiAIProvider` adapter for strict event extraction, low-text-page multimodal recovery, embeddings, and grounded answer generation. Added embedding-space provenance, safe invalidation/rebuild behavior for SQLite and pgvector, mocked provider tests, and an optional live verification script. Phase 5 UI, knowledge search, RAG orchestration, and copilot UI remain unstarted.
- 2026-09-30 — Live Gemini verification passed with `gemini-3.5-flash` for extraction/synthesis and `gemini-embedding-2` at 768 dimensions. A uniquely modified demo PDF bypassed the known SHA-256 cache, produced the validated Barail MUD_LOSS event on page 2, rendered the exact stored page as PNG, retrieved the Barail chunk at cosine similarity `0.808262`, and returned a grounded answer containing only the supplied source ID. The verifier now uses isolated temporary SQLite/storage so it cannot pollute the deterministic demo corpus. Bounded retries handle Gemini 429/5xx responses; invalid structured output still receives exactly one validation retry.
- 2026-09-30 — Phases 5, 7, and 8: added structured evidence search with well/formation/hazard filters, hybrid top-six retrieval, an evidence-only Gemini copilot with strict source-ID enforcement, insufficient-evidence behavior, and a visibly labelled deterministic evidence-summary fallback. Added the compact Knowledge and Wells workspaces, a closed-by-default 460 px copilot drawer, citation-to-page navigation, intentional loading/error/empty states, restrained transitions, reduced-motion handling, and Escape-close behavior. The final exact Phase 8 sequence passed 5/5 with Watch at sequence 10 / 3225.5 m and Elevated at sequence 40 / 3287.0 m; one run used live Gemini and four exercised the deterministic fallback, all with at least two citations and Clear@0 final reset. Forced Gemini, map-style, WebSocket, and Supabase failures were visible and controlled; Supabase now automatically degrades to the seeded SQLite/local-file path in demo mode and reports that state through health/UI. Validation finished at 47 backend tests plus frontend lint, typecheck, and production build.
- 2026-10-03 — Copilot entity-routing correction: known formation names and exact NWIS well names now act as retrieval anchors even when the question contains no hazard keyword. An explicitly named formation overrides the current live formation and bypasses current-alert well scoping, while genuinely unrelated questions still return the evidence-insufficient guardrail. The live question `what is barail` returned a bounded operational description with five exact sources; backend coverage increased to 50 passing tests.
- 2026-10-03 — Visual-only polish: promoted `Ask AI`, simplified the operational status to `LIVE`, removed demo/synthetic wording from the live workspace, added persistent light/dark modes, and added the understated national-purpose footer. India Overview now overlays the official Survey of India generalized 1:16M national boundary with visible provenance while retaining the existing MapLibre basemap, markers, clusters, radius behavior, and camera controls. No backend, replay, scoring, alert, evidence, ingestion, API, or copilot behavior changed.

## 2026-09-30 — Phase 0 complete

- Bootstrapped the React/TypeScript/Vite frontend and FastAPI backend with root development commands.
- Added deterministic SQLAlchemy seed loading for one active well, six offsets, formations, six historical events, and exact-page evidence records.
- Added shared repository interfaces with SQLite and PostgreSQL/Supabase implementations, PostgreSQL + pgvector migrations, and local/Supabase storage adapters.
- Added a 140-sample CSV replay service with deterministic start, pause, resume, and reset behavior.
- Added `GET /api/health` and idempotent `POST /api/demo/reset` endpoints.
- Added six backend tests covering fresh/repeated seeding, required seed records, replay determinism, reset idempotency, and local storage safety.
- Verified frontend lint, typecheck, production build, backend tests, backend startup, frontend startup, health, and repeated reset locally.
- Live Supabase startup was not exercised because this workspace has no project URL, database URL, or service-role key; the implementation and migrations are present for credentialed verification.

## 2026-09-30 — Phases 1–2 complete

- Built the compact industrial app shell, instrument-style context strip, interactive MapLibre offset map, radius filtering, selected-well drawer, formation track, hazard horizon, and four-chart telemetry strip.
- Added backend formation lookup, relative-position projection, Haversine distance, analog relevance, hazard-specific telemetry corroboration, evidence scoring, and state calculation.
- Added WebSocket replay controls with a one-second stream and automatic REST polling fallback; the frontend retains a 120-sample rolling window.
- Added unit coverage for every scoring and projection function plus the complete seeded risk transition.
- Verified both transports produce `CLEAR` on reset, `WATCH` at sequence 0 / 3205.0 m, and `ELEVATED` at sequence 34 / 3274.7 m.

## 2026-09-30 — Phase 1–2 correction and demo-pacing pass

- Relocated the synthetic seven-well cluster to a compact Rajasthan demo block near Barmer and added explicit synthetic-geography labeling.
- Shifted the seeded Barail mud-loss intervals deeper while preserving formation-relative projection math, producing a true Clear opening and measured transitions at sequence 10 and sequence 40.
- Added a configurable `LIVE_CORROBORATION_THRESHOLD` so `Elevated` requires meaningful live telemetry support in addition to historical recurrence.
- Refined the MapLibre hierarchy with a NWIS monogram, local-radius framing, attribution, hover details, selected-well emphasis, alert-support rings, a cleaner radius treatment, and a gridded offline fallback.
- Strengthened the Hazard Horizon bit marker, depth label, 150 m bracket, formation labels, projected markers, alert callout, and contained Clear empty state.
- Re-ran all backend scoring/projection tests and frontend lint/typecheck after the correction.

## 2026-09-30 — Focused national map correction

- Added an explicit `well_scope` boundary: the active well and six `LOCAL_OFFSET` wells remain the only inputs to radius filtering, projection, scoring, the Hazard Horizon, and alerts.
- Added 24 deterministic, synthetic `CONTEXT` wells across six Indian petroleum regions for map context only; they carry no formations, historical events, or alert intelligence.
- Moved context rendering to a clustered MapLibre GeoJSON source with zoom-interpolated pixel radii, compact count symbols, and synthetic-well hover details.
- Added restrained `Active Area` and `India Overview` camera modes. The national view hides the local search radius and suppresses local alert emphasis; returning to the active area restores operational styling and radius controls.
- Preserved fixed-pixel DOM markers for the seven interactive operational wells, with smaller country-view sizing and the existing active, selected, support, and replay states at local zoom.
- Added camera-zoom marker bands after field review: manual zoom-out now hides the six local offsets below zoom 6.5, keeps only an 8 px active-area diamond, and suppresses pulse/support decoration until operational zoom so the Rajasthan cluster cannot stack into a country-spanning stripe.
- Verified the seeded alert sequence is unchanged: Watch at sequence 10 / 3225.5 m, Elevated at sequence 40 / 3287.0 m, projected hazard at 3375.2 m with three supporting wells.
- Validation: 23 backend tests passed; frontend lint, typecheck, and production build passed.
