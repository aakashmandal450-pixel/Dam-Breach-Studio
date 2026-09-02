/**
 * 3-D impulse-wave generation & propagation (VAW / Heller–Hager style).
 *
 * Phase 12 full rewrite. The previous version used a simplified single-wave
 * model (cos²(γ) directional falloff, one amplitude/height pair, r^-1 mean
 * decay) explicitly flagged as provisional/unverified. This version matches
 * the live VAW workbook's "Generation | Propagation (3D)" sheet formulas
 * exactly (Eq. 3.22-3.35), confirmed by recalculating the sheet with
 * LibreOffice headless and diffing every intermediate value against this
 * code — not hand re-derived. See validation/README.md.
 *
 * Unlike the 2D model, VAW's 3D model has no single "peak wave" — it tracks
 * three separate wave components (leading crest, trough, second crest),
 * each with its own directional SECH-based decay, and a near-field
 * boundary that is itself direction-dependent (an ellipse combining the
 * along-axis and perpendicular boundary radii):
 *
 *   P    = F · S^{1/2} · M^{1/4} · cos^{1/2}(α · 6/7)         [Eq. 3.11, same as 2D]
 *
 *   r0,0°  = 2.5 (P B cosα')^{1/4} h                           [Eq. 3.22]
 *   r0,90° = b/2 + 1.5 (P cosα')^{1/4} h                       [Eq. 3.23]
 *   r0(γ)  = √[ r0,0² r0,90² / (r0,0² sin²γ + r0,90² cos²γ) ]  [Eq. 3.24, ellipse]
 *   r*     = r − r0(γ)                                        [Eq. 3.25]
 *
 * where cosα' = cos(6/7 · α). Near-field amplitude components at r0(γ):
 *   a0,c1 = 0.20 (P)^{1/2} B^{3/4} cosα'^{1/4} h    [Eq. 3.26, leading crest]
 *   a0,t1 = 0.35 (P B cosα')^{1/2} h                 [Eq. 3.27, trough]
 *   a0,c2 = 0.14 (P B cosα')^{1/4} h                 [Eq. 3.28, second crest]
 *
 * For r ≥ r0(γ) (VAW gives no formula inside the near field — the sheet
 * literally prints "r < r_0" there), each component decays as:
 *   a_i(r,γ) = a0,i · exp[-k_i (a0,i/h)^{-0.3} √(r_star/h)] ·
 *              sech(c_i · γ/90°)^{ cosα' · exp(-0.15 √(r_star/h)) }
 * with (k, c) = (0.4, 3.2) for c1, (0.4, 3.6) for t1, (0.1, 3.0) for c2
 * [Eq. 3.29-3.31]. Then:
 *   cc1 = 0.95 √[g(h+ac1)],  cc2 = 0.70 √[g(h+ac2)]           [Eq. 3.32-3.33]
 *   T1  = [10 ((ac1+at1)/h)^{0.2} + r_star/(2h)] √(h/g)            [Eq. 3.34]
 *   L1  = T1 · cc1                                             [Eq. 3.35]
 *
 * All limitation ranges match VAW Table 3-3 exactly (previous values were
 * a different, unsourced set — also fixed here).
 */

import type { Impulse3DInputs, Impulse3DLimits, Impulse3DResult } from "./types";

const G = 9.81;
const RHO_W = 1000;

function clampMin(v: number, eps = 1e-9): number {
  return Math.max(v, eps);
}

function sech(x: number): number {
  return 1 / Math.cosh(x);
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
  const alphaRad = (p.alphaDeg * Math.PI) / 180;
  const gammaRad = (p.gammaDeg * Math.PI) / 180;
  const r = Math.max(p.r, 0);
  const nFrac = Math.min(Math.max(p.nPercent, 0), 99) / 100;

  // Dimensionless groups (VAW Table 3-3)
  const F = Vs / Math.sqrt(G * h);
  const S = s / h;
  const mass = p.rhoS * vol; // bulk mass, no porosity reduction (matches VAW M20 / gen2d.ts fix)
  const M = mass / (RHO_W * b * h * h);
  const D = p.rhoS / RHO_W;
  const rhoGRatio = p.rhoS / (1 - nFrac) / RHO_W;
  const Vrel = vol / (b * h * h);
  const B = b / h;
  const Rrel = r / h;

  const cosTerm = Math.max(Math.cos((6 / 7) * alphaRad), 0);
  const P = F * Math.sqrt(S) * Math.pow(clampMin(M), 0.25) * Math.sqrt(cosTerm);

  // Near-field boundary geometry (Eq. 3.22-3.25)
  const r0_0 = 2.5 * Math.pow(clampMin(P) * B * cosTerm, 0.25) * h;
  const r0_90 = b / 2 + 1.5 * Math.pow(clampMin(P) * cosTerm, 0.25) * h;
  const sinG = Math.sin(gammaRad);
  const cosG = Math.cos(gammaRad);
  const ellipseDenom = r0_0 * r0_0 * sinG * sinG + r0_90 * r0_90 * cosG * cosG;
  const r0Gamma = ellipseDenom > 0 ? Math.sqrt((r0_0 * r0_0 * r0_90 * r0_90) / ellipseDenom) : r0_0;
  const rStar = r - r0Gamma;

  // Near-field amplitude components at the boundary (Eq. 3.26-3.28)
  const a0c1 = 0.2 * Math.pow(clampMin(P), 0.5) * Math.pow(B, 0.75) * Math.pow(cosTerm, 0.25) * h;
  const a0t1 = 0.35 * Math.pow(clampMin(P) * B * cosTerm, 0.5) * h;
  const a0c2 = 0.14 * Math.pow(clampMin(P) * B * cosTerm, 0.25) * h;

  const insideNearField = r < r0Gamma;

  let ac1: number | null = null;
  let at1: number | null = null;
  let ac2: number | null = null;
  let cc1: number | null = null;
  let cc2: number | null = null;
  let T1: number | null = null;
  let L1: number | null = null;

  let aM: number;
  let HM: number;
  let TM: number;
  let cRM: number;
  let LM: number;

  if (!insideNearField) {
    const rStarSafe = Math.max(rStar, 0);
    const sqrtRstar = Math.sqrt(rStarSafe / h);
    const decayBase = cosTerm * Math.exp(-0.15 * sqrtRstar);
    const gammaFrac = p.gammaDeg / 90;

    ac1 = a0c1 * Math.exp(-0.4 * Math.pow(clampMin(a0c1) / h, -0.3) * sqrtRstar) * Math.pow(sech(3.2 * gammaFrac), decayBase);
    at1 = a0t1 * Math.exp(-0.4 * Math.pow(clampMin(a0t1) / h, -0.3) * sqrtRstar) * Math.pow(sech(3.6 * gammaFrac), decayBase);
    ac2 = a0c2 * Math.exp(-0.1 * Math.pow(clampMin(a0c2) / h, -0.3) * sqrtRstar) * Math.pow(sech(3.0 * gammaFrac), decayBase);

    cc1 = 0.95 * Math.sqrt(G * (h + ac1));
    cc2 = 0.7 * Math.sqrt(G * (h + ac2));
    T1 = (10 * Math.pow((ac1 + at1) / h, 0.2) + rStarSafe / (2 * h)) * Math.sqrt(h / G);
    L1 = T1 * cc1;

    aM = ac1;
    HM = ac1 + at1;
    TM = T1;
    cRM = cc1;
    LM = L1;
  } else {
    // Screening fallback only — VAW has no formula inside r0(γ). Uses the
    // near-field boundary amplitudes directly (r* clamped to 0 in the T1
    // form) so run-up/breach chaining still has a representative number.
    // Not a VAW-verified value; flagged via insideNearField.
    aM = a0c1;
    HM = a0c1 + a0t1;
    cRM = 0.95 * Math.sqrt(G * (h + a0c1));
    TM = (10 * Math.pow((a0c1 + a0t1) / h, 0.2)) * Math.sqrt(h / G);
    LM = TM * cRM;
    warnings.push(
      `r = ${r.toFixed(1)} m is inside the near-field boundary r0(γ) = ${r0Gamma.toFixed(1)} m — VAW defines no far-field formula here; showing a near-field-boundary estimate instead.`,
    );
  }

  const limits: Impulse3DLimits = {
    F: limitCheck(F, 0.4, 3.4),
    S: limitCheck(S, 0.15, 0.6),
    M: limitCheck(M, 0.25, 1.0),
    D: limitCheck(D, 0.59, 1.72),
    rhoGRatio: limitCheck(rhoGRatio, 0.96, 2.75),
    V: limitCheck(Vrel, 0.187, 0.75),
    B: limitCheck(B, 0.83, 5.0),
    R: limitCheck(Rrel, 1, 16),
    P: limitCheck(P, 0.13, 2.08),
    alpha: limitCheck(p.alphaDeg, 30, 90),
    n: limitCheck(p.nPercent, 30.7, 43.3),
    gamma: limitCheck(p.gammaDeg, -90, 90),
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
    rhoGRatio,
    Vrel,
    B,
    Rrel,
    gammaDeg: p.gammaDeg,
    P,
    r0_0,
    r0_90,
    r0Gamma,
    rStar,
    a0c1,
    a0t1,
    a0c2,
    insideNearField,
    ac1,
    at1,
    ac2,
    cc1,
    cc2,
    T1,
    L1,
    aM,
    HM,
    TM,
    rM: r0Gamma,
    cRM,
    LM,
    limits,
    warnings,
  };
}
