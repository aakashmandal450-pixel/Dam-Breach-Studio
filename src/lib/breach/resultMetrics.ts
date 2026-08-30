import type { SimResult, SimStep, StudioInputs } from "@/lib/breach/types";

/** BREACH-GUI-style summary derived from a formation run. */
export interface BreachSummaryMetrics {
  Qpeak: number;
  tPeak_s: number;
  tPeak_min: number;
  /** Time failure starts (first active erosion / open / headcut / growing pipe). */
  tB_s: number | null;
  tB_min: number | null;
  /** Rising-limb duration TP − TB (s). */
  tRS_s: number | null;
  tRS_min: number | null;
  tCollapse_s: number | null;
  tHeadcutBreach_s: number | null;
  tEmpty_s: number | null;
  volumeReleased_m3: number;
  finalWb_m: number;
  finalDepth_m: number;
  finalWtop_m: number;
  Q0_m3s: number;
  maxTau_Pa: number;
  finalWL_m: number;
  finalZb_m: number;
  /** Breach side slope Z = (Wtop − Wb) / (2 × depth), evaluated at the peak-discharge step. */
  peakSideSlope: number | null;
  /** Velocity through the breach opening at the peak-discharge step. */
  peakVelocity_ms: number | null;
}

/** First time the breach is actively forming (BREACH-like TB). */
export function timeFailureStarts(series: SimStep[]): number | null {
  for (const s of series) {
    if (s.stage === "headcut" || s.stage === "open" || s.stage === "empty") return s.t;
    if (s.stage === "piping" && s.R > (series[0]?.R ?? 0) * 1.05 + 0.01) return s.t;
  }
  return null;
}

/** Breach discharge only, with the constant spillway component removed. */
export function breachDischarge(step: SimStep, spillwayQ: number): number {
  return Math.max(step.Q - spillwayQ, 0);
}

/** Head across the breach opening (pool level above the breach invert). */
export function breachHead(step: SimStep): number {
  return Math.max(step.WL - step.zb, 0);
}

/** Breach side slope Z = (Wtop − Wb) / (2 × depth). Null when there's no meaningful opening yet. */
export function breachSideSlope(step: SimStep): number | null {
  const depth = breachHead(step);
  if (depth <= 0.01) return null;
  return (step.Wtop - step.Wb) / (2 * depth);
}

/**
 * Velocity through the breach opening, using the average of top and bottom
 * width as a simple trapezoidal cross-section approximation — the same
 * "flow rate and velocity through the breach" check HEC-RAS guidance
 * recommends for spotting an undersized or too-fast breach.
 */
export function breachVelocity(step: SimStep, spillwayQ: number): number | null {
  const depth = breachHead(step);
  const avgWidth = (step.Wb + step.Wtop) / 2;
  const area = avgWidth * depth;
  if (area <= 0.01) return null;
  return breachDischarge(step, spillwayQ) / area;
}

export function computeBreachSummary(result: SimResult, inputs: StudioInputs): BreachSummaryMetrics {
  const series = result.series;
  const first = series[0];
  const last = series[series.length - 1];
  const tB = timeFailureStarts(series);
  const tRS = tB != null && result.tPeak >= tB ? result.tPeak - tB : null;
  const volReleased = first && last ? Math.max(0, first.V - last.V) : 0;
  const tauMax = series.reduce((m, s) => Math.max(m, s.tau), 0);

  const peakStep =
    series.reduce<SimStep | null>((best, s) => (best === null || s.Q > best.Q ? s : best), null) ?? null;

  return {
    Qpeak: result.Qpeak,
    tPeak_s: result.tPeak,
    tPeak_min: result.tPeak / 60,
    tB_s: tB,
    tB_min: tB != null ? tB / 60 : null,
    tRS_s: tRS,
    tRS_min: tRS != null ? tRS / 60 : null,
    tCollapse_s: result.tCollapse,
    tHeadcutBreach_s: result.tHeadcutBreach,
    tEmpty_s: result.tEmpty,
    volumeReleased_m3: volReleased,
    finalWb_m: result.finalWb,
    finalDepth_m: result.finalDepth,
    finalWtop_m: last?.Wtop ?? 0,
    Q0_m3s: first?.Q ?? 0,
    maxTau_Pa: tauMax,
    finalWL_m: last?.WL ?? 0,
    finalZb_m: last?.zb ?? 0,
    peakSideSlope: peakStep ? breachSideSlope(peakStep) : null,
    peakVelocity_ms: peakStep ? breachVelocity(peakStep, inputs.spillwayQ) : null,
  };
}

export type ExportKind =
  | "summary"
  | "hydrograph"
  | "rating"
  | "breach"
  | "reservoir"
  | "diagnostics"
  | "full";

export type ColumnKey =
  | keyof SimStep
  | "t_hr"
  | "t_min"
  | "depth"
  | "head"
  | "Qbreach"
  | "Qspillway"
  | "velocity"
  | "sideSlope";

export function seriesColumns(kind: ExportKind): { key: ColumnKey; header: string; unit: string }[] {
  const t = [
    { key: "t" as const, header: "t", unit: "s" },
    { key: "t_min" as const, header: "t", unit: "min" },
    { key: "t_hr" as const, header: "t", unit: "h" },
  ];
  if (kind === "hydrograph") {
    return [
      ...t,
      { key: "Q", header: "Q total", unit: "m³/s" },
      { key: "Qbreach", header: "Q breach", unit: "m³/s" },
      { key: "Qspillway", header: "Q spillway", unit: "m³/s" },
      { key: "stage", header: "stage", unit: "—" },
    ];
  }
  if (kind === "rating") {
    return [
      ...t,
      { key: "head", header: "head", unit: "m" },
      { key: "Qbreach", header: "Q breach", unit: "m³/s" },
      { key: "Q", header: "Q total", unit: "m³/s" },
      { key: "stage", header: "stage", unit: "—" },
    ];
  }
  if (kind === "breach") {
    return [
      ...t,
      { key: "Wb", header: "Wb", unit: "m" },
      { key: "Wtop", header: "Wtop", unit: "m" },
      { key: "zb", header: "zb", unit: "m" },
      { key: "depth", header: "head", unit: "m" },
      { key: "sideSlope", header: "Z", unit: "H:V" },
      { key: "xHeadcut", header: "xh", unit: "m" },
      { key: "R", header: "R", unit: "m" },
      { key: "stage", header: "stage", unit: "—" },
    ];
  }
  if (kind === "reservoir") {
    return [
      ...t,
      { key: "WL", header: "WL", unit: "m" },
      { key: "V", header: "V", unit: "m³" },
      { key: "stage", header: "stage", unit: "—" },
    ];
  }
  if (kind === "diagnostics") {
    return [
      ...t,
      { key: "tau", header: "tau", unit: "Pa" },
      { key: "velocity", header: "v", unit: "m/s" },
      { key: "R", header: "R", unit: "m" },
      { key: "xHeadcut", header: "xh", unit: "m" },
      { key: "stage", header: "stage", unit: "—" },
    ];
  }
  // full
  return [
    ...t,
    { key: "Q", header: "Q total", unit: "m³/s" },
    { key: "Qbreach", header: "Q breach", unit: "m³/s" },
    { key: "Qspillway", header: "Q spillway", unit: "m³/s" },
    { key: "WL", header: "WL", unit: "m" },
    { key: "zb", header: "zb", unit: "m" },
    { key: "Wb", header: "Wb", unit: "m" },
    { key: "Wtop", header: "Wtop", unit: "m" },
    { key: "sideSlope", header: "Z", unit: "H:V" },
    { key: "velocity", header: "v", unit: "m/s" },
    { key: "R", header: "R", unit: "m" },
    { key: "xHeadcut", header: "xh", unit: "m" },
    { key: "tau", header: "tau", unit: "Pa" },
    { key: "V", header: "V", unit: "m³" },
    { key: "stage", header: "stage", unit: "—" },
  ];
}

export function cellValue(s: SimStep, key: string, spillwayQ = 0): string | number {
  if (key === "t_min") return Number((s.t / 60).toFixed(4));
  if (key === "t_hr") return Number((s.t / 3600).toFixed(5));
  if (key === "depth" || key === "head") return Number(breachHead(s).toFixed(4));
  if (key === "xHeadcut") return Number((s.xHeadcut ?? 0).toFixed(4));
  if (key === "Qbreach") return Number(breachDischarge(s, spillwayQ).toFixed(4));
  if (key === "Qspillway") return Number(Math.max(spillwayQ, 0).toFixed(4));
  if (key === "velocity") {
    const v = breachVelocity(s, spillwayQ);
    return v != null ? Number(v.toFixed(4)) : "—";
  }
  if (key === "sideSlope") {
    const z = breachSideSlope(s);
    return z != null ? Number(z.toFixed(3)) : "—";
  }
  const v = s[key as keyof SimStep];
  if (typeof v === "number") return Number(v.toFixed(4));
  return String(v ?? "");
}
