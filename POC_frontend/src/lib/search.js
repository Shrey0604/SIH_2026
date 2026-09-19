import { OFFSET_WELLS, INCIDENT_TYPES } from "@/data/wells";

const STOP = new Set(
  "in the a an of at on show wells well with past incidents incident about any me what for formation and to from history events event all below above near happened has have that which was were is are do did how fix fixed resolved find list give tell".split(" ")
);

const haystack = (w, i) =>
  [
    i.id, w.id, w.name, w.field, i.formation, w.formation, i.date, i.cause, i.remedy,
    INCIDENT_TYPES[i.type].label, INCIDENT_TYPES[i.type].aliases, `${i.depth} m`, `${i.depth}m`,
  ].join(" ").toLowerCase();

const hit = (hay, tok) => hay.includes(tok) || (tok.length > 4 && hay.includes(tok.slice(0, -1)));

export function searchKnowledge(query) {
  const tokens = query.toLowerCase().replace(/[^a-z0-9\s-]/g, " ").split(/\s+/).filter((t) => t && !STOP.has(t));
  if (!tokens.length) return null;
  const rows = OFFSET_WELLS.flatMap((w) => w.incidents.map((i) => ({ well: w, incident: i, hay: haystack(w, i) })));
  const scored = rows
    .map((r) => ({ ...r, score: tokens.filter((t) => hit(r.hay, t)).length }))
    .filter((r) => r.score > 0);
  const full = scored.filter((r) => r.score === tokens.length);
  const results = (full.length ? full : scored).sort((a, b) => b.score - a.score || a.well.distanceKm - b.well.distanceKm);
  return {
    query,
    partial: !full.length,
    results: results.map(({ well, incident }) => ({ well, incident })),
    wellIds: new Set(results.map((r) => r.well.id)),
    incidentIds: new Set(results.map((r) => r.incident.id)),
  };
}


