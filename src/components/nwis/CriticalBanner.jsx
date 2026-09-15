import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, FileSearch, Check } from "lucide-react";
import { MATCHED } from "@/data/wells";
import { fmtDepth } from "@/lib/format";

export const CriticalBanner = ({ show, risk, depth, onViewCase, onAck }) => (
  <AnimatePresence>
    {show && (
      <motion.div
        data-testid="slide-in-critical-alert-banner"
        initial={{ y: -96, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: -96, opacity: 0 }}
        transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
        className="fixed top-4 inset-x-0 mx-auto z-50 w-[min(980px,92vw)]"
      >
        <div className="glass border border-nw-crit/70 rounded-xl px-5 py-4 flex items-center gap-4" style={{ boxShadow: "0 0 50px -8px rgba(239,68,68,.55), inset 0 1px 0 rgba(255,255,255,.04)" }}>
          <div className="relative shrink-0">
            <span className="absolute inset-0 rounded-full bg-nw-crit/40" style={{ animation: "crit-ping 1.2s ease-out infinite" }} />
            <div className="relative w-11 h-11 rounded-full bg-nw-crit/15 border border-nw-crit/60 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-nw-crit" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-display font-semibold tracking-[0.12em] text-nw-crit text-xs uppercase" data-testid="critical-banner-title">
              Critical · stuck-pipe risk {Math.round(risk)}% · {fmtDepth(depth)} m MD
            </div>
            <p className="text-sm text-nw-text/90 mt-1 leading-snug" data-testid="critical-banner-message">
              Signature matches <span className="font-semibold text-nw-text">{MATCHED.well.id}</span> differential sticking at {fmtDepth(MATCHED.incident.depth)} m ({MATCHED.incident.formation}, {MATCHED.well.distanceKm} km SW).
              Reduce WOB, keep the string moving, prepare a pipe-freeing pill.
            </p>
          </div>
          <button className="btn btn-danger shrink-0" onClick={onViewCase} data-testid="critical-banner-view-case-button">
            <FileSearch className="w-3.5 h-3.5" /> Case file
          </button>
          <button className="btn shrink-0" onClick={onAck} data-testid="critical-banner-acknowledge-button">
            <Check className="w-3.5 h-3.5" /> Acknowledge
          </button>
        </div>
      </motion.div>
    )}
  </AnimatePresence>
);


