# RESEARCH_NOTES.md — External Validation Used for the Plan

These notes are for the team, not for the live product.

## Problem statement

Public mirrors identify the Oil India challenge as:

`SIH26121 — eRTMAC-NWIS (Nearby Wells Intelligence System): An AI-Powered Offset Well Knowledge and Decision Support Platform for Drilling Operations`

The public problem statement lists:
- AI/NLP/OCR report extraction
- nearby-well map
- searchable knowledge repository
- depth/formation correlation
- predictive risk analytics
- real-time alerts/recommendations
- user-friendly dashboard

No official public dataset link is listed in the public mirrors.

## WITSML

Energistics identifies WITSML as the upstream industry data-exchange standard covering drilling, completions, interventions, logs, trajectories, and near-real-time transfer.

Current public Energistics documentation states:
- WITSML v2.1 is current
- ETP v1.2 is the transfer protocol for WITSML v2.1

Conclusion:
Use WITSML/ETP as a credible production integration path, not as a hackathon P0 requirement.

## Public petroleum data

Equinor's Volve open-data release contains roughly 40,000 files and includes:
- reports
- well data
- well technical data
- real-time drilling data
- subsurface/production data

Conclusion:
Use a tiny curated Volve subset to validate petroleum-document ingestion if convenient.
Do not make the final demo depend on downloading or processing the full dataset.

## Map stack

MapLibre GL JS is an open-source browser vector-map renderer.

OpenFreeMap documents a MapLibre-compatible public style endpoint and Vite usage.

Conclusion:
MapLibre + OpenFreeMap is sufficient for the prototype and avoids requiring a commercial map token.

## Supabase / vectors

Supabase documents pgvector support for:
- storing embeddings
- vector similarity
- semantic search

Conclusion:
Supabase Postgres + pgvector is a good hosted hackathon data layer.
The tiny corpus does not require ANN tuning.

## OpenAI

Current OpenAI documentation lists GPT-5.6 Terra as a cost/intelligence-balanced model and supports modern models through the Responses API.

The plan therefore:
- keeps model IDs environment-configurable
- uses a current general model for extraction/copilot
- uses a dedicated embeddings model for RAG

## Judging

Published SIH guidance and event reports repeatedly emphasize:
- novelty
- feasibility/practicability
- impact
- user experience
- future progression/scalability
- presentation
- working prototype quality

Exact local/finale weightings can differ.

Conclusion:
The product is optimized around a memorable, working, end-to-end demo rather than maximum feature count.

## Competitive scan

Public SIH26121 repositories already show teams exploring:
- broad AI assistants
- knowledge graphs
- local LLMs
- anomaly detection
- real-world Volve data
- spatial/stratigraphic correlation

Conclusion:
Do not try to differentiate with more technology names.
Differentiate through:
- a clear Formation-Aware Look-Ahead Hazard Horizon
- real live replay
- source-grounded alert explanations
- unusually polished operator UX
- honest model limitations
