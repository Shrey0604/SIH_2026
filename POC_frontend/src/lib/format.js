const depthFmt = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const intFmt = new Intl.NumberFormat("en-IN");

export const fmtDepth = (v) => depthFmt.format(v);
export const fmtInt = (v) => intFmt.format(v);
export const fmtTime = (d) => d.toLocaleTimeString("en-GB", { hour12: false });
export const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

const DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
export const compass = (deg) => DIRS[Math.round((((deg % 360) + 360) % 360) / 45) % 8];


