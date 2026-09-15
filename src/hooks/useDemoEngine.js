import { useState, useEffect, useMemo, useCallback } from "react";
import { SCENARIO, WINDOW, CRITICAL_T, ANOMALY_START, SCRIPTED_ALERTS, T_MAX, pointAt } from "@/data/scenario";

export const phaseOf = (r) => (r >= 75 ? "critical" : r >= 45 ? "elevated" : "normal");

export function useDemoEngine() {
  const [tick, setTick] = useState(0);
  const [running, setRunning] = useState(true);
  const [session, setSession] = useState(0);
  const [startedAt, setStartedAt] = useState(() => Date.now());

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setTick((t) => (t >= T_MAX ? t : t + 1)), 1000);
    return () => clearInterval(id);
  }, [running]);

  const current = pointAt(tick);
  const points = useMemo(() => SCENARIO.slice(tick, tick + WINDOW + 1), [tick]);
  const phase = phaseOf(current.risk);
  const criticalHit = tick >= CRITICAL_T;

  const alerts = useMemo(
    () =>
      SCRIPTED_ALERTS.filter((a) => a.t <= tick)
        .map((a) => ({ ...a, time: new Date(startedAt + a.t * 1000) }))
        .reverse(),
    [tick, startedAt]
  );

  const replay = useCallback(() => {
    setTick(0);
    setStartedAt(Date.now());
    setSession((s) => s + 1);
    setRunning(true);
  }, []);

  const skip = useCallback(() => {
    const target = ANOMALY_START - 3;
    if (tick >= target) return;
    setStartedAt((s) => s - (target - tick) * 1000);
    setTick(target);
    setRunning(true);
  }, [tick]);

  return { tick, running, setRunning, current, points, phase, criticalHit, alerts, replay, skip, session };
}


