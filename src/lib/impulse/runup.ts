/**
 * Wave run-up and overtopping (rigid dam) — VAW-style screening forms.
 * Symbols follow Figure A-1: a, H, h, β, f, b_K, R, V, d_0, …
 *
 * Run-up (simplified Kastinger / VAW style for the leading crest):
 *   ε = a / h
 *   R / h ≈ f(ε, β, a/H, c/√(gh))
 * For screening we use a robust solitary-wave style fit:
 *   R/h = 2 ε exp(0.4 ε) · (90°/β)^0.2 · (a/H)^(-0.5)   clamped to physical bounds
 *
 * Overtopping volume per unit crest length (when R > f):
 *   effective freeboard excess Δ = R − f
 *   V ≈ 0.3 · √g · Δ^1.5 · T*     (order-of-magnitude unit discharge integral)
 * These are screening relations; outside published envelopes show warnings.
 */

export interface RunupInputs {
  /** Wave crest amplitude a [m] */
  a: number;
  /** Wave height H [m] (crest to trough) */
  H: number;
  /** Still water depth h [m] */
  h: number;
  /** Run-up / dam face angle β [°] from horizontal */
  betaDeg: number;
  /** Freeboard f [m] */
  f: number;
  /** Dam crest width b_K [m] */
  bK: number;
  /** Optional wave period for volume estimate [s] */
  T?: number;
}

export interface RunupResult {
  epsilon: number;
  nonlinearity: number;
  R: number;
  overtops: boolean;
  /** Overtopping volume per unit crest length [m³/m] */
  V: number;
  /** Max overtopping flow depth on crest d_0 [m] */
  d0: number;
  /** Overtopping duration estimate [s] */
  tO: number;
  /** Average unit discharge [m²/s] */
  qm: number;
  warnings: string[];
}

export function computeRunup(p: RunupInputs): RunupResult {
  const warnings: string[] = [];
  const h = Math.max(p.h, 1e-6);
  const a = Math.max(p.a, 0);
  const H = Math.max(p.H, a);
  const beta = Math.min(Math.max(p.betaDeg, 5), 90);
  const f = Math.max(p.f, 0);
  const bK = Math.max(p.bK, 0);
  const T = p.T && p.T > 0 ? p.T : 8;

  const epsilon = a / h;
  const nonlinearity = a / H;

  if (epsilon < 0.007 || epsilon > 0.7) {
    warnings.push(`ε = a/h = ${epsilon.toFixed(3)} outside typical run-up envelope 0.007–0.70`);
  }
  if (beta < 10 || beta > 90) {
    warnings.push(`β = ${beta}° outside 10–90° envelope`);
  }

  // Screening run-up height
  const betaFactor = Math.pow(90 / beta, 0.2);
  const nonlinFactor = Math.pow(Math.max(nonlinearity, 0.3), -0.5);
  let R_h = 2 * epsilon * Math.exp(0.4 * epsilon) * betaFactor * Math.min(nonlinFactor, 2.5);
  R_h = Math.min(R_h, 3.5); // hard cap
  const R = R_h * h;

  const overtops = R > f;
  let V = 0;
  let d0 = 0;
  let tO = 0;
  let qm = 0;

  if (overtops) {
    const excess = R - f;
    d0 = Math.max(0.05 * excess, Math.min(excess * 0.45, excess));
    // Duration scales with period and crest width damping
    tO = T * (0.6 + 0.15 * Math.min(bK / Math.max(h, 0.1), 2));
    V = 0.28 * Math.sqrt(9.81) * Math.pow(excess, 1.5) * tO;
    qm = tO > 0 ? V / tO : 0;

    if (epsilon < 0.013 || epsilon > 0.7) {
      warnings.push(`Overtopping ε outside 0.013–0.70 envelope`);
    }
  }

  return { epsilon, nonlinearity, R, overtops, V, d0, tO, qm, warnings };
}
