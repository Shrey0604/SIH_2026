# DEMO_DATA.md — Deterministic Demo Fixture

## Data strategy

Use a hybrid approach:

1. **Synthetic Oil-India-like operational fixture**
   - gives complete control over formation tops, incident timing, alert thresholds, and the demo narrative
   - must be visibly labelled synthetic

2. **Public petroleum documents where convenient**
   - use a tiny curated subset of Equinor's public Volve dataset to validate ingestion/parsing behavior
   - do not ship or claim the entire Volve dataset
   - preserve public-source attribution in metadata

The final judging replay should never depend on downloading Volve data live.

---

# Active well

`NWIS-ACT-01`

Synthetic coordinates place the active well and six local offsets in a compact
local-operating cluster around the Barmer region of western Rajasthan, India. The UI labels this geography
`Rajasthan Demo Block, India • synthetic`.

Active location:
- latitude: 25.7552
- longitude: 71.3924

Active formation intervals:

| Formation | Top MD | Base MD |
|---|---:|---:|
| Tipam | 2800 m | 3090 m |
| Barail | 3090 m | 3520 m |
| Kopili | 3520 m | 3860 m |

Start replay:
- MD ≈ 3205 m
- inside Barail

Primary projected hazard:
- around 3375 m active MD

The hazard begins outside the 150 m window. Recurring analogs enter the horizon
after roughly ten replay samples, creating a visible Clear-to-Watch transition.

---

# Offset wells

Use six synthetic offset wells.

Create different formation tops/bases so raw-depth matching is visibly wrong.

Example Barail intervals:

| Well | Barail top | Barail base | Mud-loss event |
|---|---:|---:|---:|
| NWIS-OFF-01 | 3020 | 3440 | 3294–3302 |
| NWIS-OFF-02 | 3150 | 3575 | 3429–3438 |
| NWIS-OFF-03 | 2960 | 3370 | 3227–3235 |
| NWIS-OFF-04 | 3065 | 3500 | none |
| NWIS-OFF-05 | 3105 | 3535 | 3379–3387 |
| NWIS-OFF-06 | 3005 | 3435 | none |

Choose incident positions so three mud-loss events project into roughly the same active-well Barail region.

Also seed:
- one historical stuck-pipe event
- one historical kick event

These should not trigger during the primary replay.

---

# National map context

The map also contains 24 deterministic `CONTEXT` wells. These points exist only
to make the synthetic India overview spatially credible; they have no formation
intervals, historical events, evidence, projections, or alert/scoring role.

Four context wells are placed in each synthetic demo region:

- Rajasthan / Barmer
- Gujarat / Cambay
- Upper Assam
- Tripura
- Krishna-Godavari
- Mumbai / western offshore

Together with the active well and six `LOCAL_OFFSET` wells, the national view
contains 31 synthetic demo wells. Names beginning `NWIS-CTX-` and the UI's demo
disclosure make clear that these are not actual Oil India well locations.

---

# Primary telemetry story

The replay should move smoothly.

## Early baseline

- flow in ≈ flow out
- stable pit volume
- moderate torque
- stable pressure
- ROP stable

State:
- Clear or low Watch depending on analog proximity

## Approach window

As projected mud-loss interval approaches:

- historical analog recurrence becomes stronger due to distance
- evidence score may enter Watch before telemetry changes

This demonstrates the system is genuinely proactive.

## Corroboration window

Then gradually:
- flow out drops below flow in
- pit volume develops a negative slope
- small pressure deviation

State:
- Elevated

Avoid a cartoonishly huge anomaly.

---

# Recommended replay length

120–150 rows.

At 1 Hz:
- 2–2.5 minute full replay

For the demo:
- alert should occur 35–55 seconds after Start

This gives time to narrate while keeping the wow moment fast.

---

# Source documents

Create at least four tiny reports:

1. `OFF-01_DDR_excerpt.pdf`
2. `OFF-02_WCR_excerpt.pdf`
3. `OFF-03_DDR_excerpt.pdf`
4. `demo_report_barail.pdf`

Each:
- 1–3 pages
- realistic engineering prose
- one explicit event
- exact depth
- formation
- historical response
- enough surrounding text to make extraction non-trivial

Do not create fake Oil India letterheads or pretend the documents are official.

Label:
`Synthetic engineering demo report`

---

# Demo report event

`demo_report_barail.pdf`

Expected extraction:

```json
{
  "hazard_type": "MUD_LOSS",
  "formation": "Barail",
  "start_md_m": 3210,
  "end_md_m": 3218,
  "severity": "MEDIUM",
  "description": "Partial circulation loss observed while drilling the Barail interval.",
  "historical_response": "Flow was reduced and the interval was monitored before drilling resumed.",
  "page_number": 2
}
```

The wording does not need to match this exactly, but the event fields must.

Implemented ingestion verification (2026-09-30):

| Field | Measured result |
|---|---|
| SHA-256 | `2fb9dc2342558d647e594e49a337f479c580102013b86e6d6da8d726f99ad634` |
| Page extraction | 3 native-text pages; OCR skipped |
| Search index | 3 page-aware chunks |
| Validated events | 1 |
| Event | `MUD_LOSS`, Barail, 3210–3218 m MD, `MEDIUM` |
| Exact evidence page | 2 |
| Evidence navigation | stored page renders as a 1012×1432 PNG |
| Provider state during Phase 4 verification | OpenAI credit balance exhausted; hash-locked verified demo cache used and labelled |
| Active provider after migration | Gemini; live verified with `gemini-3.5-flash` |

The cached result is available only for this exact known-file hash in demo mode. It
still passes the same strict schema, formation, page-number, and evidence-substring
verification used for live model output. It remains the fallback after the Gemini
migration and is never presented as a live model result. Unknown documents fail visibly when the AI
provider is unavailable; they cannot create event or evidence records.

Gemini migration live verification (2026-09-30):

| Check | Measured result |
|---|---|
| Input | uniquely modified copy of the known demo PDF |
| Extraction source | live Gemini; verified-cache flag `false` |
| Extraction / synthesis model | `gemini-3.5-flash` |
| Extracted event | `MUD_LOSS`, Barail, 3210–3218 m MD, `MEDIUM` |
| Exact evidence | page 2; evidence excerpt verified against page text |
| Source render | page 2 rendered as `image/png`, 79,647 bytes |
| Search index | 3 page-aware chunks with live Gemini vectors |
| Embedding model | `gemini-embedding-2`, 768 dimensions |
| Similarity result | Barail mud-loss page-2 chunk, cosine similarity `0.808262` |
| Grounded answer | one supplied page-2 source ID returned; no invented citation |

The live verification runs against isolated temporary SQLite and local storage. The
normal demo database remains unchanged and resettable.

---

# Demo validation table

Before freeze, fill this in with actual values from the implemented backend:

| Check | Expected |
|---|---|
| Start formation | Barail |
| First Watch seq | 10 at 3225.5 m MD |
| Elevated seq | 40 |
| Elevated MD | 3287.0 m |
| Projected hazard MD | 3375.2 m |
| Supporting wells | 3 |
| Main hazard | MUD_LOSS |
| Copilot source count | >= 2 |

Do not hardcode the displayed acceptance numbers until the real implementation is tested.
