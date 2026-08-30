import type { SimResult, StudioInputs } from "./types";
import { runBreachSimulation } from "./engine";

export interface UncertaintyBand {
  deltaI: number;
  I_low: number;
  I_base: number;
  I_high: number;
  Qp_low: number;
  Qp_base: number;
  Qp_high: number;
  tPeak_low: number;
  tPeak_base: number;
  tPeak_high: number;
  tHeadcut_base: number | null;
  note: string;
}

/** Three-point band on erosion index I (dominant parameter). */
export function runUncertaintyBand(base: StudioInputs, deltaI = 0.5): UncertaintyBand {
  const d = Math.max(0.1, Math.min(1.5, deltaI));
  const I0 = base.erosionIndexI;
  const lowI = Math.max(0.2, I0 - d);
  const highI = Math.min(6.5, I0 + d);

  const rBase = runBreachSimulation(base);
  const rLow = runBreachSimulation({ ...base, erosionIndexI: lowI }); // more erodible → higher Qp expected
  const rHigh = runBreachSimulation({ ...base, erosionIndexI: highI });

  // Sort by Qp for display low/base/high discharge
  const runs = [
    { I: lowI, r: rLow },
    { I: I0, r: rBase },
    { I: highI, r: rHigh },
  ].sort((a, b) => a.r.Qpeak - b.r.Qpeak);

  return {
    deltaI: d,
    I_low: lowI,
    I_base: I0,
    I_high: highI,
    Qp_low: runs[0].r.Qpeak,
    Qp_base: rBase.Qpeak,
    Qp_high: runs[2].r.Qpeak,
    tPeak_low: runs[0].r.tPeak,
    tPeak_base: rBase.tPeak,
    tPeak_high: runs[2].r.tPeak,
    tHeadcut_base: rBase.tHeadcutBreach,
    note: `Qp band from I = ${lowI.toFixed(2)} (more erodible) … ${highI.toFixed(2)} (more resistant). Lower I usually raises peak discharge.`,
  };
}
