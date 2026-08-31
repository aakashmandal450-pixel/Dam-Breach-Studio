/**
 * 3-D impulse-wave generation & propagation (VAW / Heller–Hager style).
 *
 * Same dimensionless groups as 2-D, with radial distance r and propagation
 * angle γ from the slide axis. Main-lobe amplitudes scale approximately with
 * cos^n(γ). Screening envelope from VAW Table 3-3 style limits.
 *
 *   aM/h ≈ (1/2) P^{4/5} · cos²(γ)     (weaker than 2-D channel confinement)
 *   HM/h ≈ (5/6) P^{4/5} · cos²(γ)
 *   rM/h ≈ 5 P^{1/2}
 * Decay beyond rM ~ (rM/r)^{1} (geometric spreading stronger than 2-D).
 *
 * NOTE (Phase 11B fix): the radial decay exponent was corrected from 2/3 to 1.
 * Heller (co-author, Heller & Spinneken 2015, Coastal Eng. 104:113–134)
 * describes r^{-1} as "an overall mean of the tests" for 3D radial decay —
 * i.e. a representative single exponent across the dataset, not a
 * P-dependent regression term the way the 2D far-field exponent is.
 * The near-field aM/h, HM/h, rM/h, and TM* coefficients above are unverified
 * against the primary source and should be treated as provisional.
 */

import type { Impulse3DInputs, Impulse3DLimits, Impulse3DResult } from "./types";

const G = 9.81;
const RHO_W = 1000;

function clampMin(v: number, eps = 1e-9): number {
  return Math.max(v, eps);
}

function limitCheck(
  value: number,
  lo: number,
  hi: number,
): { lo: number; hi: number; value: number; ok: boolean } {
  return { lo, hi, value, ok: value >= lo && value <= hi };
}

export function computeImpulse3D(p: Impulse3DInputs): Impulse3DResult {
  const warnings: string[] = [];
  const h = clampMin(p.h);
  const b = clampMin(p.b);
  const s = clampMin(p.s);
  const Vs = clampMin(p.Vs);
  const vol = clampMin(p.slideVolume);
  const n = Math.min(Math.max(p.nPercent, 0), 80) / 100;
  const alphaRad = (p.alphaDeg * Math.PI) / 180;
  const gammaRad = (p.gammaDeg * Math.PI) / 180;
  const r = Math.max(p.r, 0);

  const F = Vs / Math.sqrt(G * h);
  const S = s / h;
  const solidVol = vol * (1 - n);
  const mass = p.rhoS * solidVol;
  const M = mass / (RHO_W * b * h * h);
  const D = p.rhoS / RHO_W;
  const Vrel = vol / (b * h * h);
  const Rrel = r / h;

  const cosTerm = Math.cos((6 / 7) * alphaRad);
  const P = F * Math.sqrt(S) * Math.pow(clampMin(M), 0.25) * Math.sqrt(Math.max(cosTerm, 0));

  // Directional reduction (main lobe at γ = 0)
  const dir = Math.pow(Math.max(Math.cos(gammaRad), 0), 2);

  const aM_h = 0.5 * Math.pow(clampMin(P), 0.8) * dir;
  const HM_h = (5 / 6) * Math.pow(clampMin(P), 0.8) * dir;
  const rM_h = 5 * Math.sqrt(clampMin(P));
  const TM_star = 9 * Math.sqrt(clampMin(P));

  const aM = aM_h * h;
  const HM = HM_h * h;
  const rM = rM_h * h;
  const TM = TM_star * Math.sqrt(h / G);
  const cRM = Math.sqrt(G * (h + aM));
  const LM = cRM * TM;

  let ar: number;
  let Hr: number;
  if (r <= 0) {
    ar = aM;
    Hr = HM;
  } else if (r < rM) {
    const ratio = r / rM;
    ar = aM * ratio;
    Hr = HM * ratio;
  } else {
    // r^-1 mean decay per Heller & Spinneken (2015) — see module docstring
    const decay = Math.pow(rM / r, 1);
    ar = aM * decay;
    Hr = HM * decay;
  }
  const Tr = TM * (r > rM ? Math.pow(r / rM, 0.15) : 1);
  const cr = Math.sqrt(G * (h + ar));
  const Lr = cr * Tr;

  const limits: Impulse3DLimits = {
    F: limitCheck(F, 0.86, 6.83),
    S: limitCheck(S, 0.09, 1.64),
    M: limitCheck(M, 0.11, 10.02),
    D: limitCheck(D, 0.59, 1.72),
    V: limitCheck(Vrel, 0.05, 5.94),
    R: limitCheck(Rrel, 2.7, 59.2),
    P: limitCheck(P, 0.17, 8.13),
    alpha: limitCheck(p.alphaDeg, 30, 90),
    n: limitCheck(p.nPercent, 30.7, 43.3),
    gamma: limitCheck(Math.abs(p.gammaDeg), 0, 90),
  };

  for (const [key, lim] of Object.entries(limits)) {
    if (!lim.ok) {
      warnings.push(
        `${key} = ${lim.value.toFixed(3)} is outside validated range [${lim.lo}, ${lim.hi}]`,
      );
    }
  }

  return {
    F,
    S,
    M,
    D,
    Vrel,
    P,
    Rrel,
    gammaDeg: p.gammaDeg,
    HM,
    aM,
    rM,
    TM,
    cRM,
    LM,
    Hr,
    ar,
    Tr,
    cr,
    Lr,
    limits,
    warnings,
  };
}
