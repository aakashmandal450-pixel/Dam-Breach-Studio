/**
 * TEMPORARY stub — replace this file with engine_FULL.ts from the v2_complete_replacement package.
 * Full V2 is in: artifacts/v2_complete_replacement/engine_FULL.ts (or engine_v2_impl.ts).
 * GitHub web: upload that file as src/lib/breach/engine.ts (overwrite).
 */
import type { SimResult, StudioInputs } from "./types";

export type MaterialClass = "cohesive" | "noncohesive";
export type ErodibilityClass = "HE" | "ME" | "LE";

export function classifyMaterial(_p: StudioInputs): MaterialClass {
  return "noncohesive";
}
export function classifyErodibility(_p: StudioInputs): ErodibilityClass {
  return "ME";
}

export function kdForMode(mode: string, I: number, tauC: number, rhoD: number, kdD: number): number {
  if (mode === "hanson") return 2e-7 * Math.pow(Math.max(tauC, 0.1), -0.5);
  if (mode === "direct") return Math.max(kdD, 0) * 1e-6;
  return Math.pow(10, -I) / Math.max(rhoD, 200);
}

export function shieldsStress(tau: number, grainDensity: number, grainD50_m: number): number {
  const G = 9.81, RHO = 1000;
  const s = Math.max(grainDensity, 1100) / RHO;
  const D50 = Math.max(grainD50_m, 1e-4);
  return tau / (Math.max(s - 1, 0.1) * RHO * G * D50);
}

export interface TransportCapacityOpts {
  grainDensity: number;
  grainD50_m: number;
  grainD90D30Ratio: number;
  criticalShields: number;
  mpmCoefficient: number;
  porosity: number;
}

export function mpmSmartErosionRate(tau: number, o: TransportCapacityOpts): number {
  const G = 9.81, RHO = 1000;
  const s = Math.max(o.grainDensity, 1100) / RHO;
  const D50 = Math.max(o.grainD50_m, 1e-4);
  const excess = tau / (Math.max(s - 1, 0.1) * RHO * G * D50) - Math.min(Math.max(o.criticalShields, 0.01), 0.2);
  if (excess <= 0) return 0;
  const phi = Math.min(Math.max(o.mpmCoefficient, 1), 16) * Math.pow(Math.max(o.grainD90D30Ratio, 1), 0.2) * Math.pow(excess, 1.5);
  const qs = phi * Math.sqrt(Math.max(s - 1, 0.1) * G * Math.pow(D50, 3));
  return qs / Math.max(1 - Math.min(Math.max(o.porosity, 0.2), 0.55), 0.45);
}

export function waveOvertopHead(
  t: number,
  o: { d0: number; tO: number; count: number; period: number },
): number {
  if (o.d0 <= 0 || o.tO <= 0) return 0;
  const period = o.period > 0 ? o.period : o.tO * 2;
  for (let k = 0; k < o.count; k++) {
    const t0 = k * period;
    if (t >= t0 && t <= t0 + o.tO) return o.d0 * Math.sin((Math.PI * (t - t0)) / o.tO);
  }
  return 0;
}

export function energyHeadcutAdvance(C: number, qUnit: number, Hdrop: number, dt: number): number {
  return Math.max(C, 0) * Math.pow(Math.max(qUnit * Math.max(Hdrop, 0), 0), 1 / 3) * Math.max(dt, 0);
}

export interface AvalancheDisplacementInputs {
  slideVolume: number;
  submergedFraction: number;
  volumeM3: number;
  initialWL: number;
  baseElev: number;
  storageExponent: number;
}
export interface AvalancheDisplacementResult {
  displacedVolumeM3: number;
  newVolumeM3: number;
  newInitialWL: number;
  deltaWL: number;
}

export function applyAvalancheDisplacement(o: AvalancheDisplacementInputs): AvalancheDisplacementResult {
  const y0 = Math.max(o.initialWL - o.baseElev, 0.05);
  const V0 = Math.max(o.volumeM3, 1);
  const m = Math.min(Math.max(o.storageExponent, 1.2), 3.5);
  const displaced = Math.max(o.slideVolume, 0) * Math.min(Math.max(o.submergedFraction, 0), 1);
  const newVolume = V0 + displaced;
  const newY = y0 * Math.pow(newVolume / V0, 1 / m);
  const newWL = o.baseElev + newY;
  return { displacedVolumeM3: displaced, newVolumeM3: newVolume, newInitialWL: newWL, deltaWL: newWL - o.initialWL };
}

export function runBreachSimulation(p: StudioInputs): SimResult {
  return runBreachSimulationV2(p);
}

export function runBreachSimulationV2(p: StudioInputs): SimResult {
  const t0 = performance.now();
  return {
    series: [],
    Qpeak: 0,
    tPeak: 0,
    tCollapse: null,
    tHeadcutBreach: null,
    tEmpty: null,
    finalWb: 0,
    finalDepth: 0,
    elapsedMs: performance.now() - t0,
    warnings: [
      "STUB ENGINE — replace src/lib/breach/engine.ts with engine_FULL.ts from v2_complete_replacement package (GitHub upload or local copy).",
    ],
    engineId: "v2",
  };
}

export function resultToCsv(result: SimResult): string {
  const header = "t,Q,WL,zb,Wb,Wtop,R,xHeadcut,tau,V,stage";
  const rows = result.series.map(
    (s) =>
      [s.t, s.Q, s.WL, s.zb, s.Wb, s.Wtop, s.R, s.xHeadcut, s.tau, s.V, s.stage].join(","),
  );
  return [header, ...rows].join("\n");
}
