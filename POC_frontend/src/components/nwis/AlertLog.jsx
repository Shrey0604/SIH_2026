import { motion, AnimatePresence } from "framer-motion";
import { fmtTime, fmtDepth } from "@/lib/format";
import { Panel } from "./ui";

const SEV = {
  INFO: { pill: "text-nw-muted border-nw-line bg-nw-bg/60", row: "border-nw-line/60", dot: "#64748B" },
  ADVISORY: { pill: "text-nw-accent border-nw-accent/40 bg-nw-accent/10", row: "border-nw-line/60", dot: "#22D3EE" },
  WARNING: { pill: "text-nw-warn border-nw-warn/50 bg-nw-warn/10", row: "border-nw-warn/40", dot: "#F59E0B" },
  CRITICAL: { pill: "text-nw-crit border-nw-crit/60 bg-nw-crit/15", row: "border-nw-crit/60 bg-nw-crit/[0.06]", dot: "#EF4444" },
};

export const AlertLog = ({ alerts }) => (
  <Panel testId="zone-6-alert-log-container" title="Alert log" subtitle={`${alerts.length} events this session · newest first`} bodyClass="p-3">
    <ol data-testid="alert-log-events-stream" className="space-y-2 max-h-[452px] overflow-y-auto nice-scroll pr-1">
      <AnimatePresence initial={false}>
        {alerts.map((a) => {
          const s = SEV[a.severity];
          return (
            <motion.li
              key={a.id}
              layout
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              data-testid={`alert-log-item-${a.id}`}
              data-severity={a.severity}
              className={`rounded-md border px-3 py-2 ${s.row}`}
            >
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] font-mono text-nw-dim tabular">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.dot, boxShadow: a.severity === "CRITICAL" ? `0 0 6px ${s.dot}` : "none" }} />
                <span>{fmtTime(a.time)}</span>
                <span className={`px-1.5 py-0.5 rounded border text-[10px] font-display font-semibold tracking-[0.12em] ${s.pill}`}>{a.severity}</span>
                <span className="ml-auto">{fmtDepth(a.depth)} m</span>
              </div>
              <p className="text-[13px] text-nw-text/90 mt-1.5 leading-relaxed">{a.message}</p>
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ol>
  </Panel>
);


