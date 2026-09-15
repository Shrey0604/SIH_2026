export const WINDOW = 40;
export const PREROLL = WINDOW;
export const ANOMALY_START = 25;
export const T_MAX = 240;

const seeded = (seed) => {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
};
const rand = seeded(20240611);
const NOISE = Array.from({ length: 512 }, () => rand() * 2 - 1);
const nz = (t, ch) => NOISE[(((t + PREROLL) * 7 + ch * 131) % 512 + 512) % 512];
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const ease = (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);

const raw = (t) => {
  const p = clamp((t - ANOMALY_START) / 9, 0, 1);
  const e = ease(p);
  const crit = p >= 1;
  return {
    t,
    wob: crit ? 25 + nz(t, 1) * 8.5 : 25 + nz(t, 1) * 0.55 + e * (3.5 + nz(t, 2) * 5.5),
    torque: crit ? 21.8 + nz(t, 3) * 1.7 : 12.1 + nz(t, 3) * 0.3 + e * (9.4 + nz(t, 4) * 1.4),
    ecd: crit ? 11.24 + nz(t, 5) * 0.05 : 10.5 + nz(t, 5) * 0.025 + e * 0.74,
    risk: crit ? 89 + nz(t, 6) * 2.2 : 16 + nz(t, 6) * 2.4 + e * 73,
    rop: crit ? 0 : Math.max(0, 18.4 + nz(t, 7) * 0.8 - e * 18.4),
  };
};

const build = () => {
  const pts = [];
  let depth = 0;
  for (let t = -PREROLL; t <= T_MAX; t++) {
    const p = raw(t);
    depth += p.rop / 60;
    pts.push({ ...p, depth });
  }
  const critIdx = pts.findIndex((p) => p.t >= 0 && p.risk >= 75);
  const offset = 3412.4 - pts[critIdx].depth;
  return pts.map((p) => ({ ...p, depth: p.depth + offset }));
};

export const SCENARIO = build();
export const pointAt = (t) => SCENARIO[clamp(t, -PREROLL, T_MAX) + PREROLL];
export const CRITICAL_T = SCENARIO.find((p) => p.t >= 0 && p.risk >= 75).t;
export const ELEVATED_T = SCENARIO.find((p) => p.t >= 0 && p.risk >= 45).t;

export const SCRIPTED_ALERTS = [
  { t: 0, severity: "INFO", message: "Telemetry link established · WITS0 feed BOG-14 · 1 Hz" },
  { t: 3, severity: "INFO", message: "Offset index loaded · 7 wells · 17 incidents within 8 km" },
  { t: 11, severity: "INFO", message: "Drilling inside safe envelope · Barail Arenaceous top prognosed at 3,410 m" },
  { t: ANOMALY_START + 2, severity: "ADVISORY", message: "Surface torque +9% vs 5-min baseline · stick-slip index rising" },
  {
    t: ELEVATED_T,
    severity: "WARNING",
    message: `Risk ELEVATED · ECD ${pointAt(ELEVATED_T).ecd.toFixed(1)} ppg approaching Barail fracture gradient · WOB erratic`,
  },
  {
    t: CRITICAL_T,
    severity: "CRITICAL",
    message: "STUCK-PIPE RISK CRITICAL · signature matches NHR-28 differential sticking (94%) · act now",
  },
  { t: CRITICAL_T + 3, severity: "INFO", message: "Case file NHR-28-01 attached · remediation playbook surfaced to driller" },
  { t: CRITICAL_T + 12, severity: "ADVISORY", message: "ROP 0 m/hr · string static · recommend immediate pipe movement and pill spot" },
].map((a, i) => ({ ...a, id: i, depth: pointAt(a.t).depth }));


