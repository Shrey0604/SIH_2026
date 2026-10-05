# Deploying NWIS

NWIS deploys as two services:

| Part | Host | Why |
|---|---|---|
| Frontend (Vite + React) | **Vercel** | Static build, global CDN |
| Backend (FastAPI) | **Render** | Needs a long-running server for WebSockets, the SQLite file, and PDF uploads — none of which work on Vercel serverless functions |

Deploy the backend first so you have its URL for the frontend.

## 1. Backend on Render

1. Go to <https://dashboard.render.com> → **New → Blueprint** and pick the `SIH_2026` GitHub repo.
   Render reads `render.yaml` at the repo root and creates the `nwis-api` web service.
2. When prompted, fill in the two secret values:
   - `GEMINI_API_KEY` — your Gemini key.
   - `FRONTEND_ORIGIN` — your Vercel URL, e.g. `https://nwis.vercel.app` (no trailing slash; comma-separate several). You can put a placeholder now and update it after step 2.
3. Wait for the deploy, then open `https://<your-service>.onrender.com/api/health`. It should return `"status":"ok"`.

On first boot the backend creates the SQLite database and seeds it from `demo_data/demo_seed.json`.

## 2. Frontend on Vercel

1. <https://vercel.com/new> → import the `SIH_2026` repo.
2. Configure the project:
   - **Application Preset:** `Vite`
   - **Root Directory:** `SIH/SIH/frontend`
   - Build / output / install settings come from `frontend/vercel.json`; leave them as default.
3. **Environment Variables:**
   - `VITE_API_BASE_URL` = `https://<your-service>.onrender.com` (the Render URL from step 1, no trailing slash)
4. Deploy. Then, if you used a placeholder, set `FRONTEND_ORIGIN` on Render to the final Vercel URL; Render redeploys automatically.

`VITE_*` variables are baked in at build time, so redeploy the frontend after changing `VITE_API_BASE_URL`.

## Things to know

- **Free-tier cold starts:** Render's free plan sleeps after ~15 minutes idle; the first request then takes ~30–60 s. Open `/api/health` a minute before a demo, or use a paid instance.
- **Ephemeral disk:** on the free plan, uploaded PDFs and anything added after boot are lost on restart or redeploy. The seeded demo data is recreated each boot. For persistence, attach a Render disk mounted at `SIH/SIH/backend/data`, or switch to the Supabase backend (`DATA_BACKEND=supabase`, see the README).
- **Gemini quota:** the free Gemini tier allows 20 generation requests per day per model. When it is exhausted, Ask NWIS falls back to a deterministic evidence summary (`provider_error` in the response says why).
- **CORS:** `FRONTEND_ORIGIN_REGEX` in `render.yaml` allows any `*.vercel.app` origin so preview deployments work. Tighten it to your project, e.g. `^https://nwis(-[a-z0-9-]+)?\.vercel\.app$`, once you know the project name.
