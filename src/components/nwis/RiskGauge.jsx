import { Crosshair, Radar, Timer } from "lucide-react";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import { MATCHED } from "@/data/wells";
import { Panel, StatusBadge, PHASE_META } from "./ui";

const polar = (cx, cy, r, deg) => {
  const a = ((deg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
};
const arc = (cx, cy, r, a0, a1) => {
  const [x0, y0] = polar(cx, cy, r, a0);
  const [x1, y1] = polar(cx, cy, r, a1);
  return `M${x0} ${y0} A${r} ${r} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1}`;
};

const Fact = ({ icon: Icon, label, value, color, testId }) => (
  <div className="rounded-lg border border-nw-line/70 bg-nw-bg/40 px-3 py-2.5 min-w-0" data-testid={testId}>
    <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-[0.12em] text-nw-dim font-display font-semibold">
      <Icon className="w-3 h-3" /> {label}
    </div>
    <div className="text-[13px] mt-1 leading-snug" style={{ color: color || "#E2E8F0" }}>{value}</div>
  </div>
);

export const RiskGauge = ({ risk, phase, criticalHit }) => {
  const shown = useAnimatedNumber(risk, 800);
  const pct = Math.max(0, Math.min(100, shown));
  const { color } = PHASE_META[phase];
  const critical = phase === "critical";
  return (
    <Panel
      testId="zone-2-risk-gauge-container"
      critical={critical}
      title="Stuck-pipe risk index"
      subtitle="Torque · ECD · WOB variance · offset similarity"
      right={<StatusBadge phase={phase} testId="risk-status-badge" />}
    >
      <div className="flex flex-col items-center">
        <div className="relative w-[250px] max-w-full h-[200px]" data-testid="radial-risk-gauge">
          {critical && <span className="absolute left-[30px] top-[30px] w-[190px] h-[190px] rounded-full border border-nw-crit/60" style={{ animation: "crit-ping 1.4s ease-out infinite" }} />}
          <svg viewBox="0 0 250 215" className="w-full h-full overflow-visible">
            <path d={arc(125, 125, 113, -135, -13.5)} stroke="#22C55E" strokeOpacity="0.45" strokeWidth="3" fill="none" />
            <path d={arc(125, 125, 113, -13.5, 67.5)} stroke="#F59E0B" strokeOpacity="0.45" strokeWidth="3" fill="none" />
            <path d={arc(125, 125, 113, 67.5, 135)} stroke="#EF4444" strokeOpacity="0.55" strokeWidth="3" fill="none" />
            <path d={arc(125, 125, 96, -135, 135)} stroke="#1B2536" strokeWidth="14" fill="none" strokeLinecap="round" />
            <path
              d={arc(125, 125, 96, -135, 135)}
              stroke={color}
              strokeWidth="14"
              fill="none"
              strokeLinecap="round"
              pathLength="100"
              strokeDasharray="100"
              strokeDashoffset={100 - pct}
              className="gauge-arc"
              style={{ filter: critical ? `drop-shadow(0 0 12px ${color})` : `drop-shadow(0 0 4px ${color}66)` }}
            />
            {[0, 25, 50, 75, 100].map((p) => {
              const [x, y] = polar(125, 125, 78, -135 + p * 2.7);
              return (
                <text key={p} x={x} y={y} fontSize="10" fill="#64748B" textAnchor="middle" dominantBaseline="middle" fontFamily="JetBrains Mono, monospace">
                  {p}
                </text>
              );
            })}
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center pt-5 pointer-events-none">
            <div className="font-mono text-[52px] font-medium tabular leading-none transition-colors duration-500" style={{ color, textShadow: critical ? `0 0 24px ${color}99` : "none" }} data-testid="risk-score-percentage">
              {Math.round(shown)}
              <span className="text-2xl text-nw-muted">%</span>
            </div>
            <div className="eyebrow mt-2">stuck-pipe risk</div>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 w-full mt-2">
          <Fact icon={Crosshair} label="Vector" value={critical ? "Differential sticking" : phase === "elevated" ? "Rising drag / ECD" : "Within envelope"} testId="risk-vector" />
          <Fact icon={Radar} label="Offset match" value={criticalHit ? `${MATCHED.well.id} · ${MATCHED.similarity}%` : "Correlating…"} color={criticalHit ? "#EF4444" : undefined} testId="risk-offset-match" />
          <Fact icon={Timer} label="ETA to stick" value={critical ? "≈ 4 min" : "—"} color={critical ? "#EF4444" : undefined} testId="risk-eta" />
        </div>
      </div>
    </Panel>
  );
};


