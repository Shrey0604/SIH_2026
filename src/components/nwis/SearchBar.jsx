import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, CornerDownLeft } from "lucide-react";
import { INCIDENT_TYPES } from "@/data/wells";
import { fmtInt, compass } from "@/lib/format";

const SUGGESTIONS = ["stuck pipe in Barail formation", "lost circulation Tipam", "kick below 2500 m", "wiper trip"];

export const SearchBar = ({ result, onSearch, onClear }) => {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const run = (text) => {
    setQ(text);
    onSearch(text);
    setOpen(true);
  };
  const clear = () => {
    setQ("");
    setOpen(false);
    onClear();
  };

  return (
    <div className="relative mt-4 z-30" data-testid="zone-5-nl-search-container">
      <form onSubmit={(e) => { e.preventDefault(); run(q); }} className="panel flex items-center gap-3 pl-4 pr-2 h-[52px]">
        <Search className="w-4 h-4 text-nw-accent shrink-0" />
        <input
          data-testid="nwis-knowledge-search-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => result && setOpen(true)}
          className="flex-1 min-w-0 bg-transparent outline-none text-sm placeholder:text-nw-dim"
          placeholder="Ask about past incidents… e.g. “stuck pipe in Barail formation”"
        />
        {(q || result) && (
          <button type="button" onClick={clear} className="text-nw-dim hover:text-nw-text p-1" data-testid="nwis-search-clear-button" aria-label="Clear search">
            <X className="w-4 h-4" />
          </button>
        )}
        <div className="hidden xl:flex items-center gap-2 pl-2 border-l border-nw-line/70">
          {SUGGESTIONS.map((s) => (
            <button key={s} type="button" className="chip" onClick={() => run(s)} data-testid="search-suggestion-chip">{s}</button>
          ))}
        </div>
        <button type="submit" className="btn btn-accent !h-9" data-testid="nwis-search-submit-button">
          Query <CornerDownLeft className="w-3.5 h-3.5" />
        </button>
      </form>

      <AnimatePresence>
        {open && result && (
          <motion.div
            data-testid="search-results-intel-card"
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.25 }}
            className="absolute left-0 right-0 top-full mt-2 glass border border-nw-line rounded-xl shadow-2xl p-4"
          >
            <div className="flex items-center justify-between">
              <div className="text-xs text-nw-muted">
                <span className="font-mono text-nw-accent">{result.results.length}</span> incident{result.results.length === 1 ? "" : "s"} across{" "}
                <span className="font-mono text-nw-accent">{result.wellIds.size}</span> well{result.wellIds.size === 1 ? "" : "s"} match <span className="text-nw-text">“{result.query}”</span>
                {result.partial && <span className="text-nw-warn"> · partial match</span>} · highlighted in the offset network below
              </div>
              <button className="text-nw-dim hover:text-nw-text text-[11px] flex items-center gap-1" onClick={() => setOpen(false)} data-testid="search-results-close-button">
                Close <span className="chip !py-0 !px-1.5 font-mono">Esc</span>
              </button>
            </div>
            {result.results.length === 0 ? (
              <p className="text-sm text-nw-muted mt-3" data-testid="search-no-results">No matching incidents in the offset archive.</p>
            ) : (
              <ul className="mt-3 grid grid-cols-1 lg:grid-cols-2 gap-2 max-h-[280px] overflow-y-auto nice-scroll pr-1">
                {result.results.slice(0, 8).map(({ well, incident }) => {
                  const t = INCIDENT_TYPES[incident.type];
                  return (
                    <li key={incident.id} className="rounded-lg border border-nw-line/70 bg-nw-bg/40 px-3 py-2.5" data-testid={`search-result-${incident.id}`}>
                      <div className="flex items-baseline gap-2 text-[11px]">
                        <span className="font-display font-semibold text-nw-text">{well.id}</span>
                        <span className="font-mono text-nw-muted tabular">{fmtInt(incident.depth)} m</span>
                        <span className="font-semibold" style={{ color: t.color }}>{t.label}</span>
                        <span className="text-nw-dim ml-auto">{incident.formation} · {well.distanceKm} km {compass(well.azimuth)}</span>
                      </div>
                      <p className="text-[11px] text-nw-muted mt-1 leading-relaxed line-clamp-2"><span className="text-nw-ok font-display font-semibold uppercase text-[9px] tracking-wider mr-1">Fix</span>{incident.remedy}</p>
                    </li>
                  );
                })}
              </ul>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};


