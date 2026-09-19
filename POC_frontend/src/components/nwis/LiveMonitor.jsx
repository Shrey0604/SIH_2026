import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { WINDOW, ANOMALY_START } from "@/data/scenario";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import { fmtDepth } from "@/lib/format";
import { Panel, LiveBadge } from "./ui";

export const SERIES = [
  { key: "wob", label: "WOB", full: "Weight on bit", unit: "klbs", color: "#22D3EE", min: 0, max: 34, base: 25, digits: 1, hot: 15 },
  { key: "torque", label: "TQ", full: "Surface torque", unit: "kft·lbf", color: "#FBBF24", min: 2, max: 26, base: 12.1, digits: 1, hot: 15 },
  { key: "ecd", label: "ECD", full: "Equiv. circ. density", unit: "ppg", color: "#A5B4FC", min: 10.1, max: 11.6, base: 10.5, digits: 2, hot: 3 },
];

const H = 300;
const DX = 1000 / (WINDOW - 1);
const TOTAL_W = WINDOW * DX;
const yOf = (s, v) => H - ((v - s.min) / (s.max - s.min)) * H;
const pathOf = (s, pts) => pts.map((p, i) => `${i ? "L" : "M"}${(i * DX).toFixed(1)} ${yOf(s, p[s.key]).toFixed(1)}`).join(" ");

const MetricTile = ({ s, value }) => {
  const v = useAnimatedNumber(value, 600);
  const delta = ((value - s.base) / s.base) * 100;
  const hot = Math.abs(delta) > s.hot;
  const Arrow = delta >= 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <div data-testid={`metric-readout-${s.key}`} className={`rounded-lg border px-4 py-3 flex-1 transition-colors duration-500 ${hot ? "border-nw-crit/50 bg-nw-crit/[0.06]" : "border-nw-line/80 bg-nw-bg/40"}`}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] tracking-[0.12em] uppercase text-nw-muted font-display font-semibold">{s.full}</span>
        <span className="w-1.5 h-1.5 rounded-full" style={{ background: s.color, boxShadow: `0 0 6px ${s.color}` }} />
      </div>
      <div className="flex items-baseline gap-2 mt-1.5">
        <span className="font-mono text-[26px] font-medium tabular leading-none text-nw-text">{v.toFixed(s.digits)}</span>
        <span className="text-[13px] text-nw-dim">{s.unit}</span>
      </div>
      <div className={`flex items-center gap-1 text-[13px] font-mono mt-1.5 tabular whitespace-nowrap ${hot ? "text-nw-crit" : "text-nw-dim"}`}>
        <Arrow className="w-3 h-3 shrink-0" />
        {Math.abs(delta).toFixed(1)}% vs base {s.base}
      </div>
    </div>
  );
};

export const LiveMonitor = ({ points, tick, phase, current }) => {
  const anomalyIdx = points.findIndex((p) => p.t >= ANOMALY_START);
  const fracY = yOf(SERIES[2], 11.1);
  return (
    <Panel
      testId="zone-1-drilling-monitor"
      critical={phase === "critical"}
      title="Live drilling monitor"
      subtitle="WITS0 · 1 Hz · rolling 40 s window · shaded region = anomaly window"
      className="lg:h-[430px]"
      right={
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="eyebrow !text-[11px]">Bit depth</div>
            <div className="font-mono text-lg font-medium tabular leading-none text-nw-accent mt-0.5" data-testid="monitor-depth-readout">
              {fmtDepth(current.depth)} <span className="text-[13px] text-nw-dim">m MD</span>
            </div>
          </div>
          <LiveBadge testId="monitor-live-indicator" />
        </div>
      }
    >
      <div className="flex flex-col lg:flex-row gap-5 h-full">
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1" data-testid="telemetry-legend">
            {SERIES.map((s) => (
              <span key={s.key} className="flex items-center gap-2 text-[13px] text-nw-muted">
                <span className="w-4 h-0.5 rounded" style={{ background: s.color }} />
                {s.label} <span className="text-nw-dim">· {s.unit}</span>
              </span>
            ))}
          </div>
          <div className="relative mt-4 h-[240px] sm:h-[280px] lg:h-auto lg:flex-1 lg:min-h-0" data-testid="telemetry-streaming-chart">
            <div className="absolute inset-0 pointer-events-none">
              {[0, 25, 50, 75, 100].map((p) => (
                <div key={p} className="absolute left-0 right-0 border-t border-dashed border-nw-line/60" style={{ top: `${p}%` }} />
              ))}
            </div>
            <div className="absolute left-1 text-[11px] font-mono text-nw-crit/60 -translate-y-full pb-0.5" style={{ top: `${(fracY / H) * 100}%` }}>
              Barail frac. gradient · 11.1 ppg
            </div>
            <div className="absolute inset-0 overflow-hidden">
              <div key={tick} className="chart-scroll h-full" style={{ width: `${(WINDOW / (WINDOW - 1)) * 100}%`, "--scroll-dx": `-${100 / WINDOW}%` }}>
                <svg viewBox={`0 0 ${TOTAL_W} ${H}`} preserveAspectRatio="none" className="w-full h-full overflow-visible">
                  {anomalyIdx >= 0 && (
                    <>
                      <rect x={anomalyIdx * DX} y={0} width={TOTAL_W - anomalyIdx * DX} height={H} fill="rgba(239,68,68,0.07)" />
                      <line x1={anomalyIdx * DX} x2={anomalyIdx * DX} y1={0} y2={H} stroke="#EF4444" strokeOpacity="0.55" strokeDasharray="4 4" vectorEffect="non-scaling-stroke" />
                    </>
                  )}
                  <line x1={0} x2={TOTAL_W} y1={fracY} y2={fracY} stroke="#EF4444" strokeOpacity="0.3" strokeDasharray="6 6" vectorEffect="non-scaling-stroke" />
                  {SERIES.map((s) => (
                    <path
                      key={s.key}
                      d={pathOf(s, points)}
                      fill="none"
                      stroke={s.color}
                      strokeWidth={s.key === "wob" ? 2 : 1.6}
                      strokeLinejoin="round"
                      strokeLinecap="round"
                      vectorEffect="non-scaling-stroke"
                      style={{ filter: `drop-shadow(0 0 4px ${s.color}80)` }}
                    />
                  ))}
                </svg>
              </div>
            </div>
            {SERIES.map((s) => (
              <span
                key={s.key}
                className="absolute right-0 w-2 h-2 rounded-full -translate-y-1/2 translate-x-1/2"
                style={{ top: `${(yOf(s, current[s.key]) / H) * 100}%`, background: s.color, boxShadow: `0 0 8px ${s.color}`, transition: "top 1s linear" }}
              />
            ))}
          </div>
          <div className="flex justify-between text-[11px] font-mono text-nw-dim mt-2 tabular">
            {["−40 s", "−30 s", "−20 s", "−10 s", "now"].map((l) => (
              <span key={l}>{l}</span>
            ))}
          </div>
        </div>
        <div className="w-full lg:w-[210px] shrink-0 flex flex-col gap-3">
          {SERIES.map((s) => (
            <MetricTile key={s.key} s={s} value={current[s.key]} />
          ))}
        </div>
      </div>
    </Panel>
  );
};


