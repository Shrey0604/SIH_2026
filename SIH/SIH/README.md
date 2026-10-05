# NWIS — Evidence-Backed Look-Ahead Intelligence

NWIS is a hackathon prototype that turns historical drilling reports into structured evidence and uses formation-relative alignment to surface hazards ahead of an active bit. The live demo data is deterministic and synthetic.

This repository contains the complete P0 prototype through **Phases 0–5, 7, and 8**: the deterministic live operator workspace, formation-aware hazard horizon, explainable scoring, exact alert-to-page evidence chain, PDF-to-validated-event ingestion, evidence search, and a secondary grounded copilot. The optional Phase 6 ML signal and Phase 9 deployment packaging remain intentionally unstarted.

## Prerequisites

- Python 3.12+
- Node.js 20+
- npm 10+

## Quick start (SQLite)

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
make install
make dev
```

Open `http://localhost:5173`. The API is at `http://localhost:8000`; health is `GET /api/health` and deterministic reset is `POST /api/demo/reset`.

Use **Documents** to upload the included `demo_data/demo_report_barail.pdf`, inspect each ingestion stage, and open the validated event's cited page. Live Gemini extraction requires `GEMINI_API_KEY`; the exact known demo file has a hash-locked, visibly labelled verified fallback so the rehearsed demo remains deterministic. Unknown PDFs fail visibly if Gemini is unavailable and never receive fabricated events.

Use **Knowledge** to filter validated, page-backed events. **Ask memory** opens the closed-by-default grounded copilot drawer; it retrieves evidence first, requires material citations, states when evidence is insufficient, and falls back to a deterministic rendering of retrieved evidence if Gemini synthesis is unavailable.

Run the processes separately with:

```bash
make backend
make frontend
```

Run validation with:

```bash
make check
npm --prefix frontend run build
```

With the development servers running, execute the exact five-run Phase 8 chain with:

```bash
.venv/bin/python scripts/smoke_demo.py
```

## Deployment

The frontend deploys to Vercel and the backend to Render. See [DEPLOY.md](DEPLOY.md) for the step-by-step guide.

## Gemini configuration

All model calls are backend-only and pass through one provider adapter. Configure the
following values in the root `.env`; never expose the API key through a `VITE_` variable:

```text
GEMINI_API_KEY=
GEMINI_EXTRACTION_MODEL=gemini-3.5-flash
GEMINI_COPILOT_MODEL=gemini-3.5-flash
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
GEMINI_EMBEDDING_DIM=768
```

Extraction uses strict JSON-schema output and Pydantic validation. Native PDF text is
preferred; Gemini multimodal recovery is called only for low-text pages. Document and
query embedding formats are centralized, and stored vectors carry provider, model, and
dimension metadata so incompatible embedding spaces are invalidated instead of mixed.

The normal test suite mocks Gemini and does not require internet access. To run the
optional live extraction, embedding, similarity-search, and grounded-answer check:

```bash
set -a; source .env; set +a
PYTHONPATH=backend .venv/bin/python scripts/verify_gemini.py
```

The verifier creates a uniquely modified PDF and uses isolated temporary SQLite and
local storage. A successful run therefore proves the live provider path without
reusing the known-file cache or changing the normal demo corpus.

## Data backends

SQLite is the guaranteed local fallback and is selected by default:

```text
DATA_BACKEND=sqlite
DATABASE_URL=sqlite:///./backend/data/nwis.db
```

For hosted Supabase, run the SQL files in `backend/migrations` in order and configure:

```text
DATA_BACKEND=supabase
DATABASE_URL=postgresql+psycopg://...
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_STORAGE_BUCKET=nwis-documents
```

The service-role key is read only by the backend. No frontend environment variable contains it. In demo mode, an unreachable Supabase configuration automatically starts the seeded SQLite/local-file fallback and exposes the degraded state through `GET /api/health` and the top-bar backend indicator.

## Determinism

On application startup, missing schema and seed records are created from `demo_data/demo_seed.json`. Seed identifiers and timestamps are fixed. Removing the local database and restarting produces the same domain data. `POST /api/demo/reset` resets replay state to sequence zero and clears transient alerts without duplicating seed data.

## Scope notes

- All seeded operational data is synthetic and is not Oil India operational data.
- The evidence score described in the product contract is a relative decision-support score, not a calibrated probability.
- Copilot output is advisory evidence synthesis only; historical mitigation is labelled `Historical response observed` and no autonomous drilling-control instruction is generated.
