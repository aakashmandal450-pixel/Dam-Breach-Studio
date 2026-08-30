import type { InflowIntervalUnit, InflowSeriesPoint } from "./types";

export function intervalToSeconds(interval: number, unit: InflowIntervalUnit): number {
  const v = Math.max(interval, 1e-9);
  if (unit === "s") return v;
  if (unit === "min") return v * 60;
  return v * 3600; // h
}

export function durationToSeconds(duration: number, unit: InflowIntervalUnit): number {
  return intervalToSeconds(duration, unit);
}

/**
 * Build a uniform time grid [0, duration] with constant Q = fillQ (default 0).
 * Last point is exactly at duration.
 */
export function buildInflowSeriesGrid(
  duration: number,
  interval: number,
  unit: InflowIntervalUnit,
  fillQ = 0,
): InflowSeriesPoint[] {
  const dt = intervalToSeconds(interval, unit);
  const T = durationToSeconds(duration, unit);
  if (!(T > 0) || !(dt > 0)) return [{ timeSec: 0, Q: fillQ }];

  const pts: InflowSeriesPoint[] = [];
  for (let t = 0; t < T - dt * 1e-9; t += dt) {
    pts.push({ timeSec: t, Q: fillQ });
  }
  // ensure end point
  if (pts.length === 0 || Math.abs(pts[pts.length - 1].timeSec - T) > 1e-6) {
    pts.push({ timeSec: T, Q: fillQ });
  } else {
    pts[pts.length - 1].timeSec = T;
  }
  // cap rows for UI safety
  if (pts.length > 500) {
    return pts.filter((_, i) => i % Math.ceil(pts.length / 500) === 0 || i === pts.length - 1);
  }
  return pts;
}

/**
 * Linear interpolation of Q_in at time t (seconds).
 * Before first / after last: hold endpoint value.
 */
export function interpolateInflow(series: InflowSeriesPoint[], tSec: number): number {
  if (!series.length) return 0;
  if (tSec <= series[0].timeSec) return Math.max(0, series[0].Q);
  const last = series[series.length - 1];
  if (tSec >= last.timeSec) return Math.max(0, last.Q);

  // binary search
  let lo = 0;
  let hi = series.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (series[mid].timeSec <= tSec) lo = mid;
    else hi = mid;
  }
  const a = series[lo];
  const b = series[hi];
  const span = b.timeSec - a.timeSec;
  if (span <= 0) return Math.max(0, a.Q);
  const w = (tSec - a.timeSec) / span;
  return Math.max(0, a.Q * (1 - w) + b.Q * w);
}

/**
 * Simple triangular / half-sine pulse for wave overtopping screening.
 * Peak Qp at t = tO/4, duration tO, volume ≈ Vtot.
 */
export function pulseHydrograph(Vtot: number, tO: number, n = 25): InflowSeriesPoint[] {
  const T = Math.max(tO, 1);
  const pts: InflowSeriesPoint[] = [];
  // Triangular: peak = 2 V / T
  const Qp = (2 * Math.max(Vtot, 0)) / T;
  for (let i = 0; i <= n; i++) {
    const t = (i / n) * T;
    const Q = t <= T / 2 ? Qp * (t / (T / 2)) : Qp * (1 - (t - T / 2) / (T / 2));
    pts.push({ timeSec: t, Q: Math.max(0, Q) });
  }
  return pts;
}
