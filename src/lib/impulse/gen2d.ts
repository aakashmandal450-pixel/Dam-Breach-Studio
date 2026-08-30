/**
 * 2-D impulse-wave generation & propagation (VAW / Heller–Hager style).
 *
 * Dimensionless groups and closed-form estimates follow the structure used in
 * the BFE VAW Manual Computational Tool (Generation | Propagation 2D).
 * Equations are the classical impulse-product forms:
 *
 *   F  = Vs / √(g h)
 *   S  = s / h
 *   M  = (ρs (1 − n) Vs_bulk) / (ρw b h²)   [relative slide mass]
 *   P  = F · S^{1/2} · M^{1/4} · cos^{1/2}(α · 6/7)   [impulse product]
 *
 *   aM / h = (3/4)  P^{4/5}
 *   HM / h = (5/4)  P^{4/5}
 *   xM / h = (11/2) P^{1/2}
 *   TM √(g/h) = 9 P^{1/2}
 *   c ≈ √[g (h + a)]   (solitary-wave estimate)
 *
 * At arbitrary X = x/h the amplitude decays approximately as
 *   a(x)/h ≈ aM/h · (xM / x)^{1/3}   for x ≥ xM
 * (with a floor at the near-field value). Period grows slowly with distance.
 *
 * All limitation ranges match Table 3-2 of the VAW tool (screening envelope).
 */

import type { Impulse2DInputs, Impulse2DLimits, Impulse2DResult } from "./types";

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

export function computeImpulse2D(p: Impulse2DInputs): Impulse2DResult {
  const warnings: string[] = [];
  const h = clampMin(p.h);
  const b = clampMin(p.b);
  const s = clampMin(p.s);
  const Vs = clampMin(p.Vs);
  const vol = clampMin(p.slideVolume);
  const n = Math.min(Math.max(p.nPercent, 0), 80) / 100; // fraction
  const alphaRad = (p.alphaDeg * Math.PI) / 180;
  const x = Math.max(p.x, 0);

  // Dimensionless groups
  const F = Vs / Math.sqrt(G * h);
  const S = s / h;
  const solidVol = vol * (1 - n);
  const mass = p.rhoS * solidVol;
  const M = mass / (RHO_W * b * h * h);
  const D = p.rhoS / RHO_W;
  const Vrel = vol / (b * h * h);
  const B = b / h;
  const X = x / h;

  // Impulse product parameter (Heller & Hager form)
  const cosTerm = Math.cos((6 / 7) * alphaRad);
  const P = F * Math.sqrt(S) * Math.pow(clampMin(M), 0.25) * Math.sqrt(Math.max(cosTerm, 0));

  // Near-field maxima
  const aM_h = 0.75 * Math.pow(clampMin(P), 0.8);
  const HM_h = 1.25 * Math.pow(clampMin(P), 0.8);
  const xM_h = 5.5 * Math.sqrt(clampMin(P));
  const TM_star = 9 * Math.sqrt(clampMin(P)); // T √(g/h)

  const aM = aM_h * h;
  const HM = HM_h * h;
  const xM = xM_h * h;
  const TM = TM_star * Math.sqrt(h / G);
  const cXM = Math.sqrt(G * (h + aM)); // solitary-wave estimate
  const LM = cXM * TM;

  // At distance x
  let ax: number;
  let Hx: number;
  if (x <= 0) {
    ax = aM;
    Hx = HM;
  } else if (x < xM) {
    // build-up zone: interpolate from 0 → max (simple ramp for screening)
    const r = x / xM;
    ax = aM * r;
    Hx = HM * r;
  } else {
    // decay ~ X^{-1/3} beyond xM
    const decay = Math.pow(xM / x, 1 / 3);
    ax = aM * decay;
    Hx = HM * decay;
  }
  // Period grows mildly with distance
  const Tx = TM * (x > xM ? Math.pow(x / xM, 0.15) : 1);
  const cx = Math.sqrt(G * (h + ax));
  const Lx = cx * Tx;

  // Limitation envelope (VAW Table 3-2 style)
  const limits: Impulse2DLimits = {
    F: limitCheck(F, 0.86, 6.83),
    S: limitCheck(S, 0.09, 1.64),
    M: limitCheck(M, 0.11, 10.02),
    D: limitCheck(D, 0.59, 1.72),
    V: limitCheck(Vrel, 0.05, 5.94),
    B: limitCheck(B, 0.74, 3.33),
    X: limitCheck(X, 2.7, 59.2),
    P: limitCheck(P, 0.17, 8.13),
    alpha: limitCheck(p.alphaDeg, 30, 90),
    n: limitCheck(p.nPercent, 30.7, 43.3),
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
    B,
    X,
    P,
    HM,
    aM,
    xM,
    TM,
    cXM,
    LM,
    Hx,
    ax,
    Tx,
    cx,
    Lx,
    limits,
    warnings,
  };
}
