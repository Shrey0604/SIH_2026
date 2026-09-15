import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Layers, X } from "lucide-react";
import { OFFSET_WELLS, INCIDENT_TYPES, MATCHED, TOTAL_INCIDENTS } from "@/data/wells";
import { fmtInt, compass } from "@/lib/format";
import { Panel, WellIcon } from "./ui";
import { OffsetMap } from "./OffsetMap";

const Timeline = ({ well, highlightIncidents }) => (
  <ol className="relative ml-2 pl-5 border-l border-nw-line/70 space-y-3 py-1" data-testid={`well-timeline-${well.id}`}>
    {[...well.incidents].sort((a, b) => b.depth - a.depth).map((i) => {
      const t = INCIDENT_TYPES[i.type];
      const hi = highlightIncidents?.has(i.id);
      return (
        <li key={i.id} className={`relative rounded-md px-3 py-2 -ml-1 transition-colors ${hi ? "bg-nw-accent/[0.07] ring-1 ring-nw-accent/40" : ""}`} data-testid={`incident-${i.id}`}>
          <span className="absolute -left-[25px] top-3 w-2.5 h-2.5 rounded-full border-2 border-nw-panel" style={{ background: t.color }} />
          <div className="flex flex-wrap items-baseline gap-x-2 text-[11px]">
            <span className="font-mono text-nw-text tabular">{fmtInt(i.depth)} m</span>
            <span className="font-display font-semibold" style={{ color: t.color }}>{t.label}</span>
            <span className="text-nw-dim">· {i.formation} · {i.date} · NPT {i.npt} h</span>
          </div>
          <p className="text-[11px] text-nw-muted mt-1 leading-relaxed"><span className="text-nw-dim uppercase tracking-wider text-[9px] font-display font-semibold mr-1">Cause</span>{i.cause}</p>
          <p className="text-[11px] text-nw-text/85 mt-0.5 leading-relaxed"><span className="text-nw-ok uppercase tracking-wider text-[9px] font-display font-semibold mr-1">Fix</span>{i.remedy}</p>
        </li>
      );
    })}
  </ol>
);

const WellRow = ({ w, selected, hi, dim, isMatch, onSelect, highlightIncidents }) => {
  const npt = w.incidents.reduce((n, i) => n + i.npt, 0);
  return (
    <li
      data-testid={`nearby-well-item-${w.id}`}
      className={`rounded-lg border transition-all duration-300 ${selected ? "border-nw-accent/50 bg-nw-accent/[0.04]" : isMatch ? "border-nw-crit/50 bg-nw-crit/[0.05]" : hi ? "border-nw-accent/40" : "border-nw-line/70 hover:border-[#3B4A63]"} ${dim ? "opacity-35" : ""}`}
    >
      <button className="w-full flex items-center gap-3 px-3 py-2.5 text-left" onClick={() => onSelect(selected ? null : w.id)} data-testid={`nearby-well-toggle-${w.id}`}>
        <span className={`w-7 h-7 rounded-md border flex items-center justify-center shrink-0 ${isMatch ? "text-nw-crit border-nw-crit/40 bg-nw-crit/10" : "text-nw-accent border-nw-line bg-nw-bg/40"}`}>
          <WellIcon className="w-3.5 h-3.5" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-baseline gap-2">
            <span className="font-display font-semibold text-sm">{w.id}</span>
            <span className="text-[11px] text-nw-muted truncate">{w.name}</span>
            {isMatch && <span className="text-[9px] font-mono text-nw-crit tracking-wider ml-auto shrink-0">MATCH {MATCHED.similarity}%</span>}
          </span>
          <span className="flex items-center gap-2 text-[11px] text-nw-dim mt-0.5">
            <span className="font-mono tabular">{w.distanceKm} km {compass(w.azimuth)}</span>
            <span>·</span>
            <span className="inline-flex items-center gap-1 text-nw-muted"><Layers className="w-3 h-3" />{w.formation}</span>
            <span>·</span>
            <span>{w.incidents.length} incidents · {npt} h NPT</span>
          </span>
        </span>
        <ChevronDown className={`w-4 h-4 text-nw-dim shrink-0 transition-transform duration-300 ${selected ? "rotate-180" : ""}`} />
      </button>
      <AnimatePresence initial={false}>
        {selected && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }} className="overflow-hidden">
            <div className="px-3 pb-3"><Timeline well={w} highlightIncidents={highlightIncidents} /></div>
          </motion.div>
        )}
      </AnimatePresence>
    </li>
  );
};

export const NearbyWells = ({ selectedId, onSelect, search, onClearSearch, criticalHit, listRef }) => {
  const ids = search?.wellIds;
  return (
    <Panel
      testId="zone-4-nearby-wells"
      title="Offset well network"
      subtitle={`${OFFSET_WELLS.length} wells · ${TOTAL_INCIDENTS} incidents indexed · 8 km radius · Upper Assam Shelf`}
      bodyClass="p-5"
      right={
        search && (
          <button className="chip !text-nw-accent !border-nw-accent/50" onClick={onClearSearch} data-testid="search-filter-clear-chip">
            “{search.query}” · {search.results.length} matches <X className="w-3 h-3" />
          </button>
        )
      }
    >
      <div className="flex gap-5 h-full">
        <div className="w-[240px] shrink-0">
          <OffsetMap selectedId={selectedId} highlightIds={ids} criticalHit={criticalHit} onSelect={(id) => onSelect(id)} />
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 px-1">
            {Object.values(INCIDENT_TYPES).map((t) => (
              <span key={t.label} className="flex items-center gap-1.5 text-[10px] text-nw-dim"><span className="w-1.5 h-1.5 rounded-full" style={{ background: t.color }} />{t.label}</span>
            ))}
          </div>
        </div>
        <ul ref={listRef} className="flex-1 min-w-0 space-y-2 max-h-[420px] overflow-y-auto nice-scroll pr-1" data-testid="nearby-wells-table-list">
          {OFFSET_WELLS.map((w) => (
            <WellRow
              key={w.id}
              w={w}
              selected={selectedId === w.id}
              hi={ids?.has(w.id)}
              dim={ids && !ids.has(w.id)}
              isMatch={criticalHit && w.id === MATCHED.well.id}
              onSelect={onSelect}
              highlightIncidents={search?.incidentIds}
            />
          ))}
        </ul>
      </div>
    </Panel>
  );
};


