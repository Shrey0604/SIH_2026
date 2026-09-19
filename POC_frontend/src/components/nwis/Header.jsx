import { Pause, Play, FastForward, RotateCcw } from "lucide-react";
import { ACTIVE_WELL } from "@/data/wells";
import { ANOMALY_START, CRITICAL_T, T_MAX } from "@/data/scenario";
import { fmtDepth, mmss } from "@/lib/format";
import { Logo, LiveBadge, Stat, PHASE_META } from "./ui";

export const Header = ({ current, tick, running, phase, onToggle, onSkip, onReplay }) => (
  <header className="flex flex-wrap items-center gap-x-6 gap-y-3 py-4 border-b border-nw-line/70" data-testid="dashboard-header">
    <div className="flex items-center gap-3 shrink-0" data-testid="nwis-brand-logo">
      <Logo />
      <div>
        <div className="font-display font-bold text-xl tracking-[0.2em] leading-none text-nw-text">NWIS</div>
        <div className="hidden sm:block text-[11px] tracking-[0.14em] uppercase text-nw-muted mt-1 whitespace-nowrap">Nearby Wells Intelligence System</div>
      </div>
    </div>
    <div className="h-9 w-px bg-nw-line hidden md:block" />
    <div className="hidden md:block min-w-0 flex-1 shrink" data-testid="header-active-well-name">
      <div className="eyebrow !text-[11px]">Active well</div>
      <div className="font-display font-semibold text-base mt-0.5 leading-none truncate">
        {ACTIVE_WELL.id}
        <span className="text-nw-muted font-normal text-sm"> · {ACTIVE_WELL.name} · {ACTIVE_WELL.field} · {ACTIVE_WELL.basin}</span>
      </div>
    </div>
    <div className="hidden lg:flex items-center gap-8 ml-2">
      <Stat label="Bit depth · MD" value={fmtDepth(current.depth)} unit="m" testId="header-depth-ticker" accent="#22D3EE" />
      <Stat label="ROP" value={current.rop.toFixed(1)} unit="m/hr" testId="header-rop" />
      <Stat label="Mud weight" value="10.6" unit="ppg" testId="header-mud-weight" />
    </div>
    <div className="ml-auto flex flex-wrap items-center gap-2 sm:gap-3 shrink-0">
      <LiveBadge testId="header-live-pulse-badge" />
      <span className="font-mono text-[13px] text-nw-muted tabular hidden sm:inline" data-testid="header-session-clock">
        T+{mmss(tick)}
      </span>
      <button className="btn" onClick={onToggle} data-testid="demo-pause-toggle-button" title={running ? "Pause stream" : "Resume stream"}>
        {running ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
        <span className="hidden xl:inline">{running ? "Pause" : "Resume"}</span>
      </button>
      <button className="btn" onClick={onSkip} disabled={tick >= ANOMALY_START - 3} data-testid="demo-skip-to-anomaly-button" style={tick >= ANOMALY_START - 3 ? { opacity: 0.45 } : undefined}>
        <FastForward className="w-3.5 h-3.5" />
        <span className="hidden xl:inline">Skip to anomaly</span>
      </button>
      <button className="btn btn-accent" onClick={onReplay} data-testid="demo-replay-control-button">
        <RotateCcw className="w-3.5 h-3.5" />
        <span className="hidden sm:inline">Replay demo</span>
      </button>
    </div>
  </header>
);

export const DemoTimeline = ({ tick, phase }) => {
  const total = T_MAX;
  const pct = Math.min(100, (tick / total) * 100);
  const color = PHASE_META[phase].color;
  const status =
    tick < ANOMALY_START ? `Anomaly onset in ${ANOMALY_START - tick}s` : tick < CRITICAL_T ? "Escalating · pattern engine correlating" : "Critical state reached · replay to reset";
  return (
    <div className="flex items-center gap-4 mt-3" data-testid="demo-timeline">
      <span className="eyebrow !text-[11px] whitespace-nowrap">Scripted scenario</span>
      <div className="relative flex-1 min-w-0 h-1.5 rounded-full bg-nw-line/70">
        <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${pct}%`, background: color, transition: "width 1s linear, background-color .6s ease", boxShadow: `0 0 10px ${color}66` }} />
        {[
          { t: ANOMALY_START, c: "#F59E0B" },
          { t: CRITICAL_T, c: "#EF4444" },
        ].map((m) => (
          <span key={m.t} className="absolute -top-[3px] w-px h-3" style={{ left: `${(m.t / total) * 100}%`, background: m.c }} />
        ))}
      </div>
      <span className="hidden md:block font-mono text-[13px] text-nw-muted whitespace-nowrap tabular" data-testid="demo-timeline-status">
        {status}
      </span>
    </div>
  );
};


