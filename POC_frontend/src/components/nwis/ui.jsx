export const Panel = ({ title, subtitle, right, children, className = "", critical = false, testId, bodyClass = "p-5" }) => (
  <section data-testid={testId} className={`panel flex flex-col min-w-0 ${critical ? "panel-critical" : ""} ${className}`}>
    {title && (
      <header className="flex items-start justify-between gap-4 px-5 pt-4 pb-3 border-b border-nw-line/70">
        <div className="min-w-0">
          <h3 className="eyebrow">{title}</h3>
          {subtitle && <p className="text-[13px] text-nw-dim mt-1 truncate">{subtitle}</p>}
        </div>
        {right}
      </header>
    )}
    <div className={`flex-1 min-h-0 ${bodyClass}`}>{children}</div>
  </section>
);

export const LiveBadge = ({ testId, label = "LIVE" }) => (
  <span
    data-testid={testId}
    className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border border-nw-ok/40 bg-nw-ok/10 text-[11px] font-display font-semibold tracking-[0.18em] text-nw-ok"
  >
    <span className="live-dot w-1.5 h-1.5 rounded-full bg-nw-ok" />
    {label}
  </span>
);

export const PHASE_META = {
  normal: { color: "#22C55E", label: "Normal envelope", short: "NORMAL" },
  elevated: { color: "#F59E0B", label: "Elevated drag", short: "ELEVATED" },
  critical: { color: "#EF4444", label: "Critical · stuck-pipe", short: "CRITICAL" },
};

export const StatusBadge = ({ phase, testId }) => {
  const m = PHASE_META[phase];
  return (
    <span
      data-testid={testId}
      className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full border text-[11px] font-display font-semibold tracking-[0.16em] uppercase whitespace-nowrap transition-colors duration-500"
      style={{ color: m.color, borderColor: `${m.color}66`, background: `${m.color}14` }}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${phase === "critical" ? "live-dot" : ""}`} style={{ background: m.color, boxShadow: `0 0 8px ${m.color}` }} />
      {m.label}
    </span>
  );
};

export const WellIcon = ({ className = "w-4 h-4" }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M9 21 12 3l3 18" />
    <path d="M5 21h14" />
    <path d="M10.4 10h3.2" />
    <path d="M9.6 15.5h4.8" />
    <path d="M12 3v-1" />
  </svg>
);

export const Logo = () => (
  <svg viewBox="0 0 40 40" className="w-10 h-10" fill="none">
    <circle cx="20" cy="20" r="18" stroke="#22D3EE" strokeOpacity="0.25" strokeWidth="1" />
    <path d="M20 5a15 15 0 0 1 15 15" stroke="#22D3EE" strokeWidth="1.5" strokeLinecap="round" />
    <path d="M20 10.5a9.5 9.5 0 0 1 9.5 9.5" stroke="#22D3EE" strokeWidth="1.5" strokeLinecap="round" strokeOpacity="0.7" />
    <path d="M14 15v9l6 8 6-8v-9z" stroke="#E2E8F0" strokeWidth="1.5" strokeLinejoin="round" />
    <path d="M14 24h12" stroke="#E2E8F0" strokeWidth="1.5" />
    <circle cx="20" cy="20" r="1.6" fill="#22D3EE" />
  </svg>
);

export const Stat = ({ label, value, unit, testId, mono = true, accent }) => (
  <div data-testid={testId} className="min-w-0">
    <div className="eyebrow !text-[11px]">{label}</div>
    <div className="flex items-baseline gap-1.5 mt-0.5">
      <span className={`${mono ? "font-mono" : "font-display"} text-lg font-medium tabular leading-none`} style={accent ? { color: accent } : undefined}>
        {value}
      </span>
      {unit && <span className="text-[13px] text-nw-dim">{unit}</span>}
    </div>
  </div>
);


