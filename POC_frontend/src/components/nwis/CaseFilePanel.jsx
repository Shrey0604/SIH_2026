import { motion, AnimatePresence } from "framer-motion";
import { Layers, MapPin, Clock, CheckCircle2, Radar, LocateFixed } from "lucide-react";
import { MATCHED, OFFSET_WELLS } from "@/data/wells";
import { fmtDepth, fmtInt, compass } from "@/lib/format";
import { Panel, WellIcon } from "./ui";

const SLIDE = { initial: { x: 48, opacity: 0 }, animate: { x: 0, opacity: 1 }, exit: { x: 48, opacity: 0 }, transition: { duration: 0.4, ease: [0.22, 1, 0.36, 1] } };

const Row = ({ label, then, now, hot }) => (
  <div className="grid grid-cols-[64px_1fr_1fr] gap-2 py-1.5 border-t border-nw-line/50 text-[13px]">
    <span className="text-nw-dim uppercase tracking-wider font-display font-semibold">{label}</span>
    <span className="text-nw-muted">{then}</span>
    <span className={`font-mono tabular ${hot ? "text-nw-crit" : "text-nw-text"}`}>{now}</span>
  </div>
);

const Block = ({ title, color, children }) => (
  <div className="pl-3 border-l-2" style={{ borderColor: color }}>
    <div className="text-[11px] uppercase tracking-[0.14em] font-display font-semibold" style={{ color }}>{title}</div>
    <p className="text-[13px] text-nw-text/90 leading-relaxed mt-1">{children}</p>
  </div>
);

const Idle = () => (
  <motion.div key="idle" {...SLIDE} className="h-full flex flex-col items-center justify-center text-center py-6" data-testid="casefile-idle-state">
    <div className="relative w-20 h-20">
      <svg viewBox="0 0 80 80" className="w-full h-full">
        {[12, 24, 36].map((r) => <circle key={r} cx="40" cy="40" r={r} fill="none" stroke="#2A3548" strokeWidth="1" />)}
        <path d="M40 40 L40 4 A36 36 0 0 1 66 14 Z" fill="url(#idleSweep)" className="radar-sweep" />
        <defs>
          <linearGradient id="idleSweep" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#22D3EE" stopOpacity="0.45" />
            <stop offset="1" stopColor="#22D3EE" stopOpacity="0" />
          </linearGradient>
        </defs>
        <circle cx="40" cy="40" r="2" fill="#22D3EE" />
      </svg>
    </div>
    <div className="font-display font-semibold text-sm mt-3">Pattern engine armed</div>
    <p className="text-[13px] text-nw-muted mt-1.5 max-w-[260px] leading-relaxed">
      Streaming the BOG-14 signature against {OFFSET_WELLS.reduce((n, w) => n + w.incidents.length, 0)} indexed incidents. A case file opens automatically when similarity exceeds 85%.
    </p>
    <div className="flex gap-2 mt-4">
      {["NHR-28", "DUL-17", "TSK-11"].map((id) => (
        <span key={id} className="chip"><Radar className="w-3 h-3" /> {id}</span>
      ))}
    </div>
  </motion.div>
);

export const CaseFilePanel = ({ criticalHit, current, onLocate }) => {
  const { well, incident, similarity, actions, alsoSimilar } = MATCHED;
  const tqDelta = Math.round((current.torque / 12.1 - 1) * 100);
  return (
    <Panel
      testId="zone-3-historical-casefile"
      critical={criticalHit}
      title="Historical context"
      subtitle={criticalHit ? "Nearest-analogue incident · offset well archive" : "Pattern engine armed · 7 offset wells indexed"}
      className="min-h-[420px] w-full"
      right={
        criticalHit && (
          <span data-testid="casefile-incident-match-chip" className="chip !border-nw-crit/60 !text-nw-crit !bg-nw-crit/10 font-mono font-semibold">
            {similarity}% match
          </span>
        )
      }
    >
      <AnimatePresence mode="wait">
        {!criticalHit ? (
          <Idle />
        ) : (
          <motion.div key="case" {...SLIDE} className="flex flex-col gap-4" data-testid="casefile-content">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg bg-nw-crit/10 border border-nw-crit/40 text-nw-crit flex items-center justify-center shrink-0">
                <WellIcon className="w-5 h-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="font-display font-semibold text-base" data-testid="casefile-well-name">{well.id}</span>
                  <span className="text-[13px] text-nw-muted truncate">{well.name} · {well.field}</span>
                </div>
                <div className="text-[11px] font-mono text-nw-dim mt-0.5">CASE FILE {incident.id} · {incident.date}</div>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  <span className="chip !text-nw-accent !border-nw-accent/40" data-testid="casefile-formation-tag"><Layers className="w-3 h-3" /> {incident.formation}</span>
                  <span className="chip"><MapPin className="w-3 h-3" /> {well.distanceKm} km {compass(well.azimuth)}</span>
                  <span className="chip font-mono">{fmtInt(incident.depth)} m MD</span>
                  <span className="chip"><Clock className="w-3 h-3" /> NPT {incident.npt} h</span>
                </div>
              </div>
            </div>

            <div data-testid="casefile-signature-table">
              <div className="grid grid-cols-[64px_1fr_1fr] gap-2 text-[11px] uppercase tracking-[0.12em] text-nw-dim font-display font-semibold pb-1">
                <span>Param</span><span>{well.id} · {incident.date}</span><span>BOG-14 · now</span>
              </div>
              <Row label="Depth" then={`${fmtInt(incident.depth)} m`} now={`${fmtDepth(current.depth)} m`} />
              <Row label="Torque" then={incident.signature.torque} now={`${current.torque.toFixed(1)} kft·lbf (+${tqDelta}%)`} hot />
              <Row label="ECD" then={incident.signature.ecd} now={`${current.ecd.toFixed(2)} ppg`} hot={current.ecd > 11.1} />
              <Row label="WOB" then={incident.signature.wob} now={`${current.wob.toFixed(1)} klbs · erratic`} hot />
            </div>

            <Block title="What happened" color="#EF4444">{incident.cause}</Block>
            <Block title="What fixed it" color="#22C55E">{incident.remedy}</Block>

            <div data-testid="casefile-corrective-actions">
              <div className="text-[11px] uppercase tracking-[0.14em] font-display font-semibold text-nw-accent">Recommended now · BOG-14</div>
              <ul className="mt-2 space-y-1.5">
                {actions.map((a, i) => (
                  <li key={i} className="flex gap-2 text-[13px] text-nw-text/90 leading-relaxed">
                    <CheckCircle2 className="w-3.5 h-3.5 text-nw-accent shrink-0 mt-0.5" /> {a}
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-nw-line/60">
              <div className="flex flex-wrap items-center gap-1.5 text-[13px] text-nw-dim">
                Also similar:
                {alsoSimilar.map((s) => (
                  <button key={s.id} className="chip font-mono" onClick={() => onLocate(s.id)} data-testid={`casefile-similar-${s.id}`}>{s.id} · {s.similarity}%</button>
                ))}
              </div>
              <button className="btn btn-accent !h-8 !px-3" onClick={() => onLocate(well.id)} data-testid="casefile-locate-button">
                <LocateFixed className="w-3.5 h-3.5" /> Locate
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Panel>
  );
};


