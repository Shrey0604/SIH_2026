import { OFFSET_WELLS, ACTIVE_WELL, MATCHED } from "@/data/wells";

const C = 130;
const SCALE = 112 / 8;
const pos = (w) => {
  const a = (w.azimuth * Math.PI) / 180;
  return [C + w.distanceKm * SCALE * Math.sin(a), C - w.distanceKm * SCALE * Math.cos(a)];
};

export const OffsetMap = ({ selectedId, highlightIds, criticalHit, onSelect }) => {
  const [mx, my] = pos(MATCHED.well);
  return (
    <svg data-testid="schematic-svg-offset-map" viewBox="0 0 260 260" className="w-full h-auto select-none">
      <defs>
        <linearGradient id="mapSweep" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#22D3EE" stopOpacity="0.28" />
          <stop offset="1" stopColor="#22D3EE" stopOpacity="0" />
        </linearGradient>
      </defs>
      {[2, 4, 8].map((km) => (
        <g key={km}>
          <circle cx={C} cy={C} r={km * SCALE} fill="none" stroke="#2A3548" strokeWidth="1" strokeDasharray={km === 8 ? "0" : "3 4"} />
          <text x={C - 6} y={C - km * SCALE - 3} fontSize="9.5" fill="#64748B" textAnchor="end" fontFamily="JetBrains Mono, monospace">{km} km</text>
        </g>
      ))}
      <line x1={C} y1={C - 112} x2={C} y2={C + 112} stroke="#2A3548" strokeWidth="0.75" />
      <line x1={C - 112} y1={C} x2={C + 112} y2={C} stroke="#2A3548" strokeWidth="0.75" />
      <path d={`M${C} ${C} L${C} ${C - 112} A112 112 0 0 1 ${C + 112 * Math.sin(0.7)} ${C - 112 * Math.cos(0.7)} Z`} fill="url(#mapSweep)" className="radar-sweep" />
      <text x={C} y={12} fontSize="9.5" fill="#64748B" textAnchor="middle" fontFamily="JetBrains Mono, monospace">N</text>

      {criticalHit && (
        <>
          <line x1={C} y1={C} x2={mx} y2={my} stroke="#EF4444" strokeWidth="1" strokeDasharray="3 3" strokeOpacity="0.8" />
          <circle cx={mx} cy={my} r="9" fill="none" stroke="#EF4444" strokeWidth="1" style={{ transformOrigin: `${mx}px ${my}px`, animation: "crit-ping 1.4s ease-out infinite" }} />
        </>
      )}

      {OFFSET_WELLS.map((w) => {
        const [x, y] = pos(w);
        const selected = w.id === selectedId;
        const hi = highlightIds?.has(w.id);
        const dim = highlightIds && !hi;
        const isMatch = criticalHit && w.id === MATCHED.well.id;
        const fill = isMatch ? "#EF4444" : selected || hi ? "#22D3EE" : "#8B9BB4";
        return (
          <g key={w.id} onClick={() => onSelect(w.id)} className="cursor-pointer" opacity={dim ? 0.3 : 1} style={{ transition: "opacity .3s ease" }} data-testid={`map-well-marker-${w.id}`}>
            <circle cx={x} cy={y} r="11" fill="transparent" />
            {(selected || hi) && <circle cx={x} cy={y} r="7.5" fill="none" stroke="#22D3EE" strokeOpacity="0.6" strokeWidth="1" />}
            <circle cx={x} cy={y} r="4" fill={fill} stroke="#0B1220" strokeWidth="1.5" style={{ filter: isMatch || selected ? `drop-shadow(0 0 5px ${fill})` : "none" }} />
            <text x={x} y={y - 8} fontSize="10" fill={isMatch ? "#FCA5A5" : selected || hi ? "#22D3EE" : "#94A3B8"} textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontWeight="500">
              {w.id}
            </text>
          </g>
        );
      })}

      <g data-testid="map-active-well-marker">
        <circle cx={C} cy={C} r="9" fill="none" stroke="#22D3EE" strokeOpacity="0.5" strokeWidth="1" style={{ transformOrigin: `${C}px ${C}px`, animation: "crit-ping 2s ease-out infinite" }} />
        <path d={`M${C} ${C - 6} L${C + 6} ${C} L${C} ${C + 6} L${C - 6} ${C} Z`} fill="#22D3EE" stroke="#0B1220" strokeWidth="1" />
        <text x={C} y={C + 17} fontSize="10" fill="#22D3EE" textAnchor="middle" fontFamily="JetBrains Mono, monospace" fontWeight="600">{ACTIVE_WELL.id}</text>
      </g>
    </svg>
  );
};


