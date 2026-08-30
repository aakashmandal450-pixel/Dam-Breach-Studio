import type { MoraineStabilityInputs, MoraineStabilityResult } from "./types";

/**
 * Distal-face infinite-slope screening with pore-pressure ratio Ru.
 *
 * FoS = [c'/(γ H cos²β) + (1 − Ru) tan φ'] / tan β
 * (classic infinite-slope form; H = dam height as characteristic depth).
 *
 * Ice/thaw: cohesion and φ reduced linearly with thaw fraction when iceCored.
 * Geometry / freeboard scores follow GLOF hazard literature (width/height, freeboard/height).
 */
export function computeMoraineStability(p: MoraineStabilityInputs): MoraineStabilityResult {
  const notes: string[] = [];
  const beta = Math.atan(1 / Math.max(p.zDown, 0.2)); // slope angle from H:1V
  const betaDeg = (beta * 180) / Math.PI;

  let c = Math.max(p.cohesion, 0); // kPa
  let phi = Math.max(p.phiDeg, 1);
  if (p.iceCored) {
    const tf = clamp(p.thawFraction, 0, 1);
    // Thaw softens: cohesion drops strongly; φ mildly
    c = c * (1 - 0.7 * tf);
    phi = phi * (1 - 0.15 * tf);
    notes.push(
      `Ice-cored thaw knockdown applied (thaw fraction ${tf.toFixed(2)}): c→${c.toFixed(1)} kPa, φ→${phi.toFixed(1)}°.`,
    );
  }

  const gamma = Math.max(p.gamma, 12); // kN/m³
  const H = Math.max(p.height, 1);
  const Ru = clamp(p.ru, 0, 0.7);
  const tanB = Math.tan(beta);
  const cos2 = Math.cos(beta) ** 2;
  const tanPhi = Math.tan((phi * Math.PI) / 180);

  // FoS infinite slope
  const num = c / (gamma * H * cos2) + (1 - Ru) * tanPhi;
  const FoS = tanB > 1e-6 ? num / tanB : 99;

  let FoS_class: MoraineStabilityResult["FoS_class"] = "stable";
  if (FoS < 1.0) FoS_class = "unstable";
  else if (FoS < 1.3) FoS_class = "marginal";

  // Geometry: crest width / height (or dam base width ratio approximated by input)
  const wh = Math.max(p.widthToHeight, 0);
  let geometryRisk: MoraineStabilityResult["geometryRisk"] = "low";
  if (wh < 0.15) geometryRisk = "high";
  else if (wh < 0.35) geometryRisk = "medium";

  const fr = Math.max(p.freeboardRatio, 0);
  let freeboardRisk: MoraineStabilityResult["freeboardRisk"] = "low";
  if (fr < 0.05) freeboardRisk = "high";
  else if (fr < 0.12) freeboardRisk = "medium";

  // Composite 0–1 hazard (higher = worse) — screening weights
  const fosScore = FoS >= 1.5 ? 0 : FoS >= 1.3 ? 0.25 : FoS >= 1.0 ? 0.55 : 0.9;
  const geoScore = geometryRisk === "high" ? 0.35 : geometryRisk === "medium" ? 0.2 : 0.05;
  const fbScore = freeboardRisk === "high" ? 0.35 : freeboardRisk === "medium" ? 0.2 : 0.05;
  const iceScore = p.iceCored ? 0.1 + 0.15 * clamp(p.thawFraction, 0, 1) : 0;
  const compositeScore = clamp(fosScore + geoScore + fbScore + iceScore, 0, 1);

  let compositeClass: MoraineStabilityResult["compositeClass"] = "low";
  if (compositeScore >= 0.75) compositeClass = "very_high";
  else if (compositeScore >= 0.55) compositeClass = "high";
  else if (compositeScore >= 0.35) compositeClass = "moderate";

  notes.push(
    "Infinite-slope FoS is a distal-face screening index, not a full limit-equilibrium or FEM strength-reduction analysis.",
  );
  notes.push(
    "Literature often flags steep distal slopes (>~1:3 → β≳18°) and low freeboard as predisposing factors for GLOF.",
  );

  return {
    betaDeg,
    FoS,
    FoS_class,
    geometryRisk,
    freeboardRisk,
    compositeScore,
    compositeClass,
    notes,
  };
}

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}
