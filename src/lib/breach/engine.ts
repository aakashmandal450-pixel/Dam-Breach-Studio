/**
 * engine.ts — Dam Breach Studio core (V2 physics, complete replacement)
 *
 * DLBreach-style A3: non-eq transport, Exner, phreatic pipe invert, HE/ME/LE,
 * adaptive Δt, gradual roof collapse, zero-freeboard notch growth.
 *
 * Also exports V1-compatible helpers used by Impulse panel and unit tests:
 *   applyAvalancheDisplacement, waveOvertopHead, energyHeadcutAdvance,
 *   kdForMode, shieldsStress, mpmSmartErosionRate, resultToCsv
 *
 * DROP-IN: replace src/lib/breach/engine.ts with this file. No UI import changes required.
 */

import type { BreachStage, EmpiricalBreachResult, SimResult, SimStep, StudioInputs } from "./types";
import { interpolateInflow } from "./inflowSeries.ts";

const G = 9.81;
const RHO = 1000;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

/** ASTM/ISO sand–silt boundary (m). */
const SILT_SAND_BOUNDARY_M = 6.2e-5; // 0.062 mm

export type MaterialClass = "cohesive" | "noncohesive";
export type ErodibilityClass = "HE" | "ME" | "LE";

/**
 * Material class for erosion closure selection.
 */
export function classifyMaterial(p: StudioInputs): MaterialClass {
  if (p.damStructure === "moraine" || p.damStructure === "ice_cored_moraine") {
    return "noncohesive";
  }
  const I = p.erosionIndexI ?? 3;
  if (I > 4.0) return "cohesive";
  const D50 = p.grainD50_m ?? 0.03;
  if (D50 < SILT_SAND_BOUNDARY_M) return "cohesive";
  return "noncohesive";
}

/**
 * Screening erodibility class (Xu/Zhang / USBR style HE–ME–LE).
 * Fine sand + moderate I → HE; high I → LE; else ME.
 * Used to scale detachment / capacity, not as a hidden Qpeak fudge.
 */
export function classifyErodibility(p: StudioInputs): ErodibilityClass {
  const I = p.erosionIndexI ?? 3;
  const D50 = p.grainD50_m ?? 0.03;
  if (I > 4.0) return "LE";
  if (I < 2.5) return "HE";
  // Fine to medium sand (0.062 mm – 2 mm) with moderate I → HE (Apishapa-like)
  if (D50 >= SILT_SAND_BOUNDARY_M && D50 < 0.002 && I <= 3.5) return "HE";
  if (I >= 3.8) return "LE";
  return "ME";
}

/** Multipliers from erodibility class (physics-oriented ranges). */
function erodibilityFactors(ec: ErodibilityClass): {
  pipeRate: number;
  openRate: number;
  widen: number;
  adaptScale: number;
} {
  switch (ec) {
    case "HE":
      return { pipeRate: 2.8, openRate: 1.8, widen: 1.6, adaptScale: 0.55 };
    case "LE":
      return { pipeRate: 0.45, openRate: 0.5, widen: 0.7, adaptScale: 1.4 };
    default:
      return { pipeRate: 1.0, openRate: 1.0, widen: 1.0, adaptScale: 1.0 };
  }
}

function shieldsTauC(D50: number, gs: number, th = 0.047) {
  return th * (Math.max(gs, 1100) / RHO - 1) * RHO * G * Math.max(D50, 1e-5);
}

export function kdForMode(mode: string, I: number, tauC: number, rhoD: number, kdD: number) {
  if (mode === "hanson") return 2e-7 * Math.pow(Math.max(tauC, 0.1), -0.5);
  if (mode === "direct") return Math.max(kdD, 0) * 1e-6;
  return Math.pow(10, -I) / Math.max(rhoD, 200);
}

function excessShear(kd: number, tau: number, tauC: number, n: number) {
  const e = Math.max(tau - tauC, 0);
  return e <= 0 ? 0 : kd * Math.pow(e, Math.max(n, 0.5));
}

export function estimatePipeInvertPhreatic(p: StudioInputs, Hb: number) {
  const base = p.baseElev;
  const head = Math.max(p.initialWL, base + 0.1 * Hb) - base;
  const alpha =
    0.28 +
    0.12 * clamp(head / Math.max(Hb, 0.5), 0.2, 1) * clamp(p.coreHeightFraction ?? 0.85, 0.4, 1);
  return clamp(base + alpha * head, base + 0.1 * Hb, p.crestElev - 0.2 * Hb);
}

interface NOpts {
  grainDensity: number;
  grainD50_m: number;
  grainD90D30Ratio: number;
  criticalShields: number;
  mpmCoefficient: number;
  porosity: number;
  adaptationLength: number;
}

function bedLoadCapacity(tau: number, o: NOpts) {
  const s = Math.max(o.grainDensity, 1100) / RHO;
  const D50 = Math.max(o.grainD50_m, 1e-4);
  const excess =
    tau / (Math.max(s - 1, 0.1) * RHO * G * D50) - clamp(o.criticalShields, 0.01, 0.2);
  if (excess <= 0) return 0;
  const phi =
    clamp(o.mpmCoefficient, 1, 16) *
    Math.pow(Math.max(o.grainD90D30Ratio, 1), 0.2) *
    Math.pow(excess, 1.5);
  return phi * Math.sqrt(Math.max(s - 1, 0.1) * G * Math.pow(D50, 3));
}

function pipeNonEq(opts: {
  Ct: number;
  tau: number;
  U: number;
  area: number;
  perimeter: number;
  pipeLength: number;
  dt: number;
  material: MaterialClass;
  kd: number;
  tauC: number;
  n: number;
  o: NOpts;
  pipeRate: number;
}) {
  const { tau, U, area, perimeter, pipeLength, dt, kd, tauC, n, pipeRate } = opts;
  const poros = clamp(opts.o.porosity, 0.2, 0.55);
  const epsShear = excessShear(kd, tau, tauC, n) * pipeRate;
  let Ct = opts.Ct;
  Ct += clamp((Math.max(U, 0.05) * dt) / Math.max(pipeLength, 1), 0, 1) * (0 - Ct);
  // Pipe-wall detachment remains excess-shear. Transport-capacity grain inputs
  // select the open-breach closure only and must not silently affect the pipe.
  const epsWall = epsShear;
  if (perimeter > 1e-6 && area > 1e-6 && epsWall > 0) {
    Ct = clamp(Ct + ((epsWall * perimeter * dt) / area) * (1 - poros), 0, 0.4);
  }
  return { CtNew: Ct, epsWall, CtStar: 0 };
}

function openNonEq(
  Ct: number,
  tau: number,
  U: number,
  h: number,
  Lb: number,
  dt: number,
  o: NOpts,
  openRate: number,
) {
  const qtStar = bedLoadCapacity(tau, o) * openRate;
  const CtStar = h > 1e-4 && U > 1e-4 ? clamp(qtStar / (U * h), 0, 0.3) : 0;
  const poros = clamp(o.porosity, 0.2, 0.55);
  const CtNew =
    Ct +
    clamp((Math.max(U, 0.05) * dt) / Math.max(o.adaptationLength, 5), 0, 0.6) * (CtStar - Ct);
  const qt = Math.max(qtStar * (1 - Ct / Math.max(CtStar, 1e-9)), 0.5 * qtStar);
  return { CtNew, qt, CtStar };
}

/**
 * Volume → shape. Post-collapse uses lower fBed / higher bank share + widen factor.
 */
function applyVol(o: {
  dA: number;
  Wb: number;
  zb: number;
  zPhi: number;
  h: number;
  baseElev: number;
  crestLength: number;
  fBed?: number;
  widen?: number;
}) {
  const f = clamp(o.fBed ?? 0.45, 0.15, 0.85);
  const widen = o.widen ?? 1;
  if (o.dA <= 0) return { Wb: o.Wb, zb: o.zb };
  const dz = (f * o.dA) / Math.max(o.Wb, 0.3);
  const dWbVol = (((1 - f) * o.dA) / Math.max(o.h, 0.3)) * widen;
  const dWbGeom = 2 * dz * o.zPhi * Math.max(widen, 1);
  const dWb = Math.max(dWbVol, dWbGeom);
  return {
    zb: Math.max(o.zb - dz, o.baseElev),
    Wb: Math.min(o.Wb + dWb, o.crestLength * 1.05),
  };
}

function pipeShear(w: number, h: number, H: number, L: number, full: boolean) {
  const area = Math.max(w * h, 1e-6);
  const Rh = area / Math.max(2 * (w + h), 1e-3);
  return RHO * G * Rh * (Math.max(H, 0) / Math.max(L, 1)) * (full ? 1 : 0.65);
}

function growPipe(w: number, h: number, eps: number, dt: number) {
  if (eps <= 0) return { w, h };
  const dA = eps * 2 * (w + h) * dt;
  return {
    w: w + (dA * 0.45) / Math.max(h, 0.05),
    h: h + (dA * 0.55) / Math.max(w, 0.05),
  };
}

function roof(o: {
  w: number;
  h: number;
  inv: number;
  crest: number;
  ratio: number;
  phi: number;
  heBoost?: number;
}) {
  const cover = Math.max(o.crest - (o.inv + o.h), 0.02);
  const full = Math.max(o.crest - o.inv, 0.5);
  const phi = Math.max(o.phi, 15) * (Math.PI / 180);
  const need =
    ((o.w ** 2) / (8 * Math.max(o.w * 0.5, 0.5))) *
    (0.35 / Math.max(Math.tan(phi), 0.2));
  // HE materials stand slightly less cover before collapse
  const ratio = o.ratio * (o.heBoost ?? 1);
  const risk = Math.max(
    o.h / (ratio * full),
    (o.w / Math.max(2.2 * cover, 0.01)) * 0.5,
    (need / cover) * 0.5,
  );
  const fails =
    o.h >= ratio * full ||
    (o.w > 2.2 * cover && o.h > 0.25 * full) ||
    (cover < need && o.h > 0.2 * full);
  return { fails, risk, cover };
}

/** Apply a morphology cap calibrated per 2 s reference interval, independent of adaptive dt. */
export function capErosionAreaPerStep(
  requestedArea: number,
  fractionPerReferenceStep: number,
  damHeight: number,
  width: number,
  dt: number,
): number {
  const referenceDt = 2; // DEFAULT_INPUTS.dt; preserves the legacy default-step cap.
  const cap =
    Math.max(fractionPerReferenceStep, 0) *
    Math.max(damHeight, 0) *
    Math.max(width, 0.5) *
    Math.max(dt, 0) / referenceDt;
  return Math.min(Math.max(requestedArea, 0), cap);
}

/** Accumulate actual invert lowering and consume it once when the collapse threshold is reached. */
export function updateBankCollapseExposure(
  currentExposure: number,
  invertLowering: number,
  triggerHeight: number,
): { exposure: number; collapseHeight: number } {
  const total = Math.max(currentExposure, 0) + Math.max(invertLowering, 0);
  if (total >= triggerHeight) return { exposure: 0, collapseHeight: total };
  return { exposure: total, collapseHeight: 0 };
}


function empiricalVonThunGillette(Hw: number, Vw: number, highlyErodible: boolean): EmpiricalBreachResult {
  const h = Math.max(Hw, 0.01);
  const v = Math.max(Vw, 0);
  const cb = v < 1.23e6 ? 6.1 : v < 6.17e6 ? 18.3 : v < 12.3e6 ? 42.7 : 54.9;
  const width = 2.5 * h + cb;
  const tf = highlyErodible ? 0.015 * h : 0.015 * h + 0.25;
  return {
    method: "von_thun_gillette",
    predictedWidthM: width,
    predictedDepthM: h,
    formationTimeH: tf,
    peakDischargeM3s: null,
    notes: ["Average breach width and formation-time screening equations.", "Peak discharge is not supplied by this implementation of Von Thun and Gillette."]
  };
}

function empiricalFroehlich(p: StudioInputs, Hw: number, Vw: number): EmpiricalBreachResult {
  const h = Math.max(Hw, 0.01);
  const v = Math.max(Vw, 0);
  const ko = p.mode === "overtopping" ? 1.3 : 1.0;
  const width = 0.27 * ko * Math.pow(Math.max(v, 1), 0.32) * Math.pow(h, 0.04);
  const tfSec = 63.2 * Math.sqrt(Math.max(v, 0) / (G * h * h));
  const qp = 0.607 * Math.pow(Math.max(v, 0), 0.295) * Math.pow(h, 1.24);
  return {
    method: "froehlich",
    predictedWidthM: Number.isFinite(width) ? width : null,
    predictedDepthM: h,
    formationTimeH: Number.isFinite(tfSec) ? tfSec / 3600 : null,
    peakDischargeM3s: Number.isFinite(qp) ? qp : null,
    notes: ["Width and formation time use the Froehlich 2008 regression; peak flow uses Froehlich 1995q.", `K0=${ko.toFixed(1)} for ${p.mode} failure.`]
  };
}

function empiricalMacDonald(
  p: StudioInputs,
  Hw: number,
  Vout: number,
  crestWidth: number,
  zSide: number,
): EmpiricalBreachResult {
  const h = Math.max(Hw, 0.01);
  const vout = Math.max(Vout, 0);
  const clayCoreOrRockfill = p.damStructure === "zoned" || p.damStructure === "ice_cored_moraine";
  const ver = clayCoreOrRockfill
    ? 0.00348 * Math.pow(Math.max(vout * h, 0), 0.852)
    : 0.0261 * Math.pow(Math.max(vout * h, 0), 0.769);
  const tf = ver > 0 ? 0.0179 * Math.pow(ver, 0.364) : 0;
  const C = Math.max(crestWidth, 0.01);
  const Zb = Math.max(zSide, 0);
  const numerator = ver - h * h * (C * Zb + (h * Zb * Zb) / 3);
  const denominator = h * (C + (h * Zb) / 2);
  const bottomWidth = denominator > 0 ? numerator / denominator : null;
  return {
    method: "macdonald",
    predictedWidthM: bottomWidth != null && Number.isFinite(bottomWidth) ? Math.max(bottomWidth, 0) : null,
    predictedDepthM: h,
    formationTimeH: Number.isFinite(tf) ? tf : null,
    peakDischargeM3s: null,
    notes: [
      `Vout=${vout.toFixed(2)} m³ and hw=${h.toFixed(2)} m were taken from the simulated run.`,
      clayCoreOrRockfill ? "Clay-core/rockfill regression branch used." : "Earthfill regression branch used.",
      "Peak discharge is not directly predicted by the implemented MacDonald–Langridge-Monopolis equations; use the simulated Qpeak for comparison."
    ]
  };
}

function buildEmpiricalResults(
  p: StudioInputs,
  series: SimStep[],
  finalDepth: number,
  zSide: number,
): EmpiricalBreachResult[] {
  if (!series.length) return [];
  let vout = 0;
  for (let i = 1; i < series.length; i++) {
    const a = series[i - 1];
    const b = series[i];
    const dt = Math.max(b.t - a.t, 0);
    vout += 0.5 * (Math.max(a.Q, 0) + Math.max(b.Q, 0)) * dt;
  }
  const last = series[series.length - 1];
  const Hw = Math.max(last.WL - last.zb, finalDepth, 0.01);
  const Vw = Math.max(last.V, 0);
  const highlyErodible = p.erosionIndexI < 2.5;
  return [
    empiricalVonThunGillette(Hw, Vw, highlyErodible),
    empiricalFroehlich(p, Hw, Vw),
    empiricalMacDonald(p, Hw, vout, p.crestWidth, zSide),
  ];
}

export function runBreachSimulationV2(p: StudioInputs): SimResult {
  const tStart = performance.now();
  const warnings: string[] = [];
  const DEBUG_HEADCUT = (globalThis as any)?.process?.env?.DBS_DEBUG_HEADCUT === "1"; // TEMP-DEBUG
  const debugRows: string[] = []; // TEMP-DEBUG
  if (DEBUG_HEADCUT) debugRows.push("t,dt,WL,h,hEff,hCr,wH,xHead,Wb,zb,Q"); // TEMP-DEBUG
  // Adaptive Δt bounds (user dt is the nominal / max step)
  const dtUser = Math.max(p.dt, 0.25);
  const dtMax = dtUser;
  const dtMin = Math.max(0.05, dtUser / 20);
  let dt = dtUser;
  const tMax = Math.max(p.tMaxHours, 0.1) * 3600;
  const recordInterval = Math.max(dtUser, tMax / 600);
  let tNextRecord = 0;
  warnings.push(
    `Adaptive Δt enabled (min=${dtMin.toFixed(2)} s, max=${dtMax.toFixed(2)} s)`,
  );

  const Hb = Math.max(p.crestElev - p.baseElev, 0.5);
  const C = Math.max(p.crestWidth, 0.5);
  const zPhi = 1 / Math.tan(Math.max(((p.phiDeg ?? 32) * Math.PI) / 180, 0.15));

  const material = classifyMaterial(p);
  const erod = classifyErodibility(p);
  const ef = erodibilityFactors(erod);
  const D50report = p.grainD50_m ?? 0.03;
  warnings.push(
    `V2 material: ${material}; erodibility: ${erod} ` +
      `(D50=${(D50report * 1000).toFixed(2)} mm, I=${p.erosionIndexI ?? 3})`,
  );
  const erosionModel = p.erosionModel ?? "excess_shear";
  const kdM = p.kdMode ?? "index";
  if (erosionModel === "transport_capacity") {
    warnings.push(
      material === "noncohesive"
        ? "Open-breach erosion closure: transport-capacity (MPM/Smart with Exner); pipe and headcut remain excess-shear."
        : "Transport-capacity requested for cohesive material; open-breach falls back to excess-shear.",
    );
  }
  if (kdM === "hanson") {
    warnings.push("Hanson & Simon JET erodibility selected; erosion exponent n is fixed at 1.");
  }

  // Overtopping now has an explicit intact-dam stage. The starter notch is created only
  // after the hydraulic erosion trigger is exceeded (unless the legacy guard is disabled).
  const intactOvertopping = p.mode === "overtopping" && p.intactOvertoppingEnabled !== false;
  const notchSeed = Math.min(
    Math.max(p.initialNotchWidth ?? 1.2, 0.2),
    Math.max(0.5, 0.15 * Math.min(p.crestLength, 40)),
  );
  const starterDepth = Math.max(
    p.starterNotchDepth ?? 0.05,
    Math.max(p.starterNotchDepthRatio ?? 0.01, 0) * Hb,
  );
  let starterActive = p.mode === "piping" || !intactOvertopping;
  let zb = starterActive
    ? Math.max(p.zb ?? p.baseElev + 0.5, p.baseElev + 0.05)
    : p.crestElev;
  let Wb = p.mode === "piping" ? 0 : starterActive ? notchSeed : 0;
  let Zb = zPhi;
  let erosionExposure = 0;
  let tErosionInitiation: number | null = null;
  let tStarterNotch: number | null = starterActive && p.mode === "overtopping" ? 0 : null;
  let tSignificantBreach: number | null = null;
  const initialNotchArea = Math.max(notchSeed * Math.max(starterDepth, 0.01), 1e-4);
  let breachDevelopmentIndex = 0;
  let trueBreachActive = false;
  const updateBreachDevelopment = (time: number) => {
    const depth = Math.max(p.crestElev - zb, 0);
    const areaRatio = (Wb * depth) / initialNotchArea;
    const widthRatio = Wb / Math.max(notchSeed, 0.2);
    const depthRatio = depth / Math.max(Hb, 0.5);
    const areaGate = Math.max(p.breachAreaRatioThreshold ?? 5, 1);
    const widthGate = Math.max(p.breachWidthRatioThreshold ?? 2.5, 1);
    const depthGate = Math.max(p.breachDepthRatioThreshold ?? 0.15, 0.01);
    const areaProgress = clamp(areaRatio / areaGate, 0, 1);
    const widthProgress = clamp(widthRatio / widthGate, 0, 1);
    const depthProgress = clamp(depthRatio / depthGate, 0, 1);
    // A geometric mean prevents one oversized dimension from saturating BDI.
    breachDevelopmentIndex = Math.cbrt(areaProgress * widthProgress * depthProgress);
    const mature = areaProgress >= 1 && widthProgress >= 1 && depthProgress >= 1;
    if (mature && !trueBreachActive) {
      trueBreachActive = true;
      tSignificantBreach = time;
      warnings.push(`Mature breach geometry established t=${(time / 3600).toFixed(4)} h`);
    }
  };

  const pipeInvert = estimatePipeInvertPhreatic(p, Hb);
  warnings.push(`Pipe invert FORCED phreatic: ${pipeInvert.toFixed(2)} m`);

  const R0 = Math.max(p.initialPipeRadius ?? 0.08, 0.02);
  let pipeW = 2 * R0;
  let pipeH = 2 * R0;
  let pipeCt = 0;
  let lastCtStar = 0;
  let lastCover = 0;
  let lastRisk = 0;

  const pipeLen = Math.max(
    p.coreLength ?? 0,
    C + 0.5 * Hb * ((p.zUp ?? 2.5) + (p.zDown ?? 2.5)),
    5,
  );
  let collapsed = p.mode !== "piping";
  let collapsing = false;
  let cProg = 0;
  let cWb = 0;
  let cZb = 0;
  // (4) Slightly faster roof transition for HE
  const CDUR = erod === "HE" ? 60 : erod === "LE" ? 120 : 90;

  let xHead = 0;
  let unsupportedBankExposure = 0;
  let headOn = false;
  const hcOn = p.headcutEnabled ?? true;
  const hcLaw = p.headcutLaw ?? "hydrostatic";
  const hcC = p.headcutEnergyCoeff ?? 0.5;
  const gFrac = p.headcutGateDeepenFraction ?? 0.25;
  const gCap = p.headcutGateDeepenCap ?? 0.015;
  const hInit = p.headcutInitDepth ?? 0.04;
  const fH = p.headcutAdvanceFactor ?? 6;
  // Breach-process corrections: transient waves can initiate erosion but must not
  // excavate an entire moraine crest in one pulse. Reservoir-driven flow controls
  // sustained breach development after initiation.
  const isMoraine = p.damStructure === "moraine" || p.damStructure === "ice_cored_moraine";
  const waveHeadcutFactor = isMoraine ? 0.04 : 0.12;
  const headcutRetardation = isMoraine ? 0.22 : erod === "HE" ? 0.55 : 0.75;
  const maxHeadcutRate = Math.max(0.002, Hb / (isMoraine ? 6 * 3600 : 2 * 3600));
  let openCt = 0;

  const adapt0 = Math.max(C * 2.5, 10) * ef.adaptScale;
  const nOpts: NOpts = {
    grainDensity: p.grainDensity ?? 2650,
    grainD50_m: p.grainD50_m ?? 0.03,
    grainD90D30Ratio: p.grainD90D30Ratio ?? 8,
    criticalShields: p.criticalShields ?? 0.047,
    mpmCoefficient: p.mpmCoefficient ?? 8,
    porosity: p.porosity ?? 0.35,
    adaptationLength: adapt0,
  };
  const poros = clamp(nOpts.porosity, 0.2, 0.55);

  const tauU = p.tauC ?? 8;
  const tauSh = shieldsTauC(
    nOpts.grainD50_m,
    nOpts.grainDensity,
    nOpts.criticalShields,
  );
  const usesTransportCapacity = erosionModel === "transport_capacity" && material === "noncohesive";
  const tauCore = usesTransportCapacity ? Math.min(tauU, tauSh) : tauU;
  const tauShell = usesTransportCapacity
    ? Math.min(p.shellTauC ?? tauU, tauSh)
    : (p.shellTauC ?? tauU);

  const kdC = kdForMode(kdM, p.erosionIndexI, tauCore, p.rhoD, p.kdDirect ?? 0.5);
  const nC = kdM === "hanson" ? 1 : (p.erosionExponent ?? 1);
  const kdS = kdForMode(
    kdM,
    p.shellErosionIndexI ?? p.erosionIndexI,
    tauShell,
    p.rhoD,
    p.kdDirect ?? 0.5,
  );
  const nS = kdM === "hanson" ? 1 : (p.shellErosionExponent ?? 1);

  let y = Math.max(p.initialWL - p.baseElev, 0.05);
  const y0 = y;
  const V0 = Math.max(p.volumeM3, 1);
  const mS = clamp(p.storageExponent ?? 2, 1.2, 3.5);
  let V = V0;

  const waveA = !!(
    p.mode === "overtopping" &&
    p.waveForcingEnabled &&
    (p.waveOvertopDepth ?? 0) > 0
  );
  if (waveA && p.mode === "overtopping") {
    warnings.push("Wave-overtopping forcing ON: wave head adds no stored volume; wave-driven crest and opening outflow are debited once from reservoir storage.");
  }
  if (hcLaw === "energy" && hcOn) {
    warnings.push(`Energy headcut law active (coefficient C=${hcC}); hydrostatic face shear still controls deepening.`);
  }
  const waveO = {
    d0: p.waveOvertopDepth ?? 0,
    tO: p.waveOvertopDuration ?? 0,
    count: Math.max(1, p.waveOvertopCount ?? 1),
    period: p.waveOvertopPeriod ?? 0,
  };

  let tCol: number | null = null;
  let tHc: number | null = null;
  let tEmp: number | null = null;
  let Qpeak = 0;
  let tPeak = 0;
  let QovertoppingPeak = 0;
  let tOvertoppingPeak = 0;
  let QstarterPeak = 0;
  let tStarterPeak = 0;
  let QbreachPeak = 0;
  let tBreachPeak = 0;
  let QtotalPeak = 0;
  let tTotalPeak = 0;
  const series: SimStep[] = [];

  warnings.push(
    `Pipe L=${pipeLen.toFixed(1)} m; HE factors pipe×${ef.pipeRate}, open×${ef.openRate}, widen×${ef.widen}`,
  );
  warnings.push(`Breach corrections: wave-triggered initiation, retarded headcut, reservoir-driven storage release`);
  if (p.mode === "overtopping") {
    warnings.push(
      intactOvertopping
        ? `Intact overtopping stage enabled: starter notch waits for hydraulic erosion trigger`
        : `Legacy overtopping seed notch enabled: Wb=${notchSeed.toFixed(2)} m`,
    );
  }

  // Collapse ratio slightly lower for HE (fails earlier)
  const collapseRatio =
    (p.collapseRatio ?? 0.55) * (erod === "HE" ? 0.85 : erod === "LE" ? 1.1 : 1);

  let t = 0;
  let step = 0;
  let Qprev = 0;
  while (t <= tMax + 1e-9) {
    const WL = p.baseElev + y;
    let Q = Math.max(p.spillwayQ, 0);
    let Qovertopping = 0;
    let QwaveExcess = 0;
    let Qstarter = 0;
    let Qbreach = 0;
    let streamPower = 0;
    let tau = 0;
    let stage: BreachStage = collapsed ? (starterActive ? "open" : "overtopping") : "piping";
    const R = Math.sqrt((pipeW * pipeH) / Math.PI);

    // ===== PIPING =========================================================
    if (!collapsed) {
      const Hp = Math.max(WL - pipeInvert, 0);
      if (Hp > 0) {
        const area = Math.max(pipeW * pipeH, 1e-8);
        const qPipe = (p.CdOrifice ?? 0.6) * area * Math.sqrt(2 * G * Hp);
        Q += qPipe;
        Qbreach += qPipe;
        tau = pipeShear(pipeW, pipeH, Hp, pipeLen, pipeH < Hp * 0.95);
        const per = 2 * (pipeW + pipeH);
        const st = pipeNonEq({
          Ct: pipeCt,
          tau,
          U: Q / area,
          area,
          perimeter: per,
          pipeLength: pipeLen,
          dt,
          material,
          kd: kdC,
          tauC: tauCore,
          n: nC,
          o: nOpts,
          pipeRate: ef.pipeRate,
        });
        pipeCt = st.CtNew;
        lastCtStar = st.CtStar;
        const g = growPipe(pipeW, pipeH, st.epsWall, dt);
        pipeW = g.w;
        pipeH = g.h;
        const rs = roof({
          w: pipeW,
          h: pipeH,
          inv: pipeInvert,
          crest: p.crestElev,
          ratio: collapseRatio,
          phi: p.phiDeg ?? 32,
          heBoost: erod === "HE" ? 0.9 : 1,
        });
        lastCover = rs.cover;
        lastRisk = rs.risk;
        if (rs.fails) {
          collapsing = true;
          collapsed = true;
          tCol = t;
          cProg = 0;
          cWb = Math.max(pipeW * (erod === "HE" ? 1.2 : 1.0), p.initialNotchWidth ?? 1);
          cZb = clamp(
            pipeInvert - Math.min(0.25 * pipeH, 0.08 * Hb),
            p.baseElev,
            p.crestElev - 0.5,
          );
          xHead = C;
          tHc = t;
          headOn = true;
          openCt = pipeCt;
          Wb = Math.max(pipeW * 0.6, 0.5);
          zb = clamp(pipeInvert, p.baseElev, p.crestElev - 0.3);
          stage = "open";
          warnings.push(`Roof failure t=${(t / 3600).toFixed(3)}h`);
        }
      } else {
        stage = "filling";
      }
    }

    // Gradual collapse
    if (collapsing && cProg < 1) {
      cProg = Math.min(1, cProg + dt / CDUR);
      const s = cProg * cProg * (3 - 2 * cProg);
      Wb = Math.max(Wb, cWb * (0.5 + 0.5 * s));
      zb = Math.min(zb, cZb + (1 - s) * Math.max(pipeInvert - cZb, 0));
      if (cProg >= 1) {
        collapsing = false;
        Wb = Math.max(Wb, cWb);
        zb = Math.min(zb, cZb);
      }
    }

    // ===== OPEN / OVERTOPPING =============================================
    if (collapsed) {
      const wH = waveA ? waveOvertopHead(t, waveO) : 0;
      const h = Math.max(WL - zb, 0);
      const hEff = h + wH;
      const hCr = Math.max(WL - p.crestElev, 0) + wH;

      // ===== CREST OVERTOPPING ============================================
      if (p.mode === "overtopping") {
        if (!starterActive) stage = "overtopping";
        if (hCr > 1e-6) {
          const crestFlowWidth = Math.max(p.crestLength, 0.5);
          const openingTopWidth = starterActive
            ? clamp(Wb + 2 * Zb * hCr, 0, crestFlowWidth)
            : 0;
          const remainingCrestWidth = Math.max(crestFlowWidth - openingTopWidth, 0);
          Qovertopping =
            (p.Cw ?? 1.7) * remainingCrestWidth * Math.pow(hCr, 1.5);
          Q += Qovertopping;
          if (!starterActive) {
            const areaFlow = Math.max(crestFlowWidth * hCr, 1e-6);
            const U = Qovertopping / areaFlow;
            const Rh = Math.max(hCr, 0.02);
            tau = (RHO * G * (p.manningN ?? 0.03) ** 2 * U * U) / Math.cbrt(Rh);
            streamPower = tau * U;

            const shearTrigger =
              tau > tauShell && hCr >= Math.max(p.overtoppingTriggerDepth ?? 0.01, 0);
            const powerTrigger = streamPower >= Math.max(p.streamPowerThreshold ?? 50, 0);
            const trigger =
              (p.erosionTriggerMode ?? "shear") === "shear_and_stream_power"
                ? shearTrigger && powerTrigger
                : shearTrigger;
            erosionExposure = trigger ? erosionExposure + dt : 0;
            if (trigger && tErosionInitiation == null) tErosionInitiation = t;

            if (trigger && erosionExposure >= Math.max(p.erosionInitiationDuration ?? 10, 0)) {
              const fullCrestQ = Qovertopping;
              starterActive = true;
              tStarterNotch = t;
              tErosionInitiation ??= t;
              zb = clamp(
                p.crestElev - starterDepth,
                p.baseElev,
                p.crestElev - 1e-4,
              );
              Wb = Math.max(notchSeed, 0.2);
              const openedWidth = clamp(Wb + 2 * Zb * hCr, 0, crestFlowWidth);
              Qovertopping =
                (p.Cw ?? 1.7) *
                Math.max(crestFlowWidth - openedWidth, 0) *
                Math.pow(hCr, 1.5);
              Q += Qovertopping - fullCrestQ;
              stage = "headcut";
              warnings.push(
                `Overtopping erosion initiated t=${(t / 3600).toFixed(4)} h; starter notch Wb=${Wb.toFixed(2)} m, depth=${starterDepth.toFixed(3)} m`,
              );
            }
          }
        }
      }

      if (starterActive && hEff > 1e-4 && WL + wH >= zb) {
        // xHead is longitudinal progress through the crest; Wb is the current
        // lateral breach width. Neither dimension is used as an arbitrary flow cap.
        const Wavg = Wb + Zb * hEff;
        const qWeir =
          (p.Cw ?? 1.7) * Math.max(Wavg, notchSeed * 0.5) * Math.pow(Math.max(hEff, 0), 1.5);
        const qWeirStanding =
          (p.Cw ?? 1.7) *
          Math.max(Wb + Zb * h, notchSeed * 0.5) *
          Math.pow(Math.max(h, 0), 1.5);
        QwaveExcess += Math.max(qWeir - qWeirStanding, 0);
        Q += qWeir;
        Qbreach += qWeir;
        // Keep the early-stage component as an overlapping diagnostic, not a
        // second discharge to add to Qbreach or reservoir storage.
        if (!trueBreachActive) Qstarter += qWeir;
        if (DEBUG_HEADCUT) debugRows.push(`${t.toFixed(2)},${dt.toFixed(3)},${WL.toFixed(3)},${h.toFixed(3)},${hEff.toFixed(3)},${hCr.toFixed(3)},${wH.toFixed(3)},${xHead.toFixed(3)},${Wb.toFixed(3)},${zb.toFixed(3)},${Q.toFixed(2)}`); // TEMP-DEBUG

        const Rh =
          (Math.max(Wavg, 0.3) * hEff) /
          Math.max(Wb + 2 * hEff * Math.sqrt(1 + Zb * Zb), 0.1);
        const U = hEff > 1e-4 ? qWeir / Math.max(Wavg * hEff, 1e-6) : 0;
        const nM = p.manningN ?? 0.03;
        tau =
          (RHO * G * nM * nM * U * U) / Math.pow(Math.max(Rh, 0.02), 1 / 3);
        streamPower = tau * U;

        const hcDone = !hcOn || xHead >= C - 1e-6;
        const Lb = Math.max(C, 3);

        if (hcOn && !hcDone) {
          if (!headOn && hCr >= hInit) headOn = true;
          // (5) Also start headcut if pool is already over crest with a notch
          if (!headOn && h > 0.02 && p.mode === "overtopping") headOn = true;
          if (headOn || hCr >= hInit) {
            headOn = true;
            // Limit transient wave contribution to scarp migration. The full wave
            // depth remains available for initiation hydraulics, but only a fraction
            // contributes to sustained headcut advance.
            const reservoirHead = Math.max(WL - Math.max(zb, p.baseElev), 0);
            const waveDrivenHead = Math.max(hCr - Math.max(WL - p.crestElev, 0), 0);
            const hF = Math.max(reservoirHead * 0.35, waveDrivenHead * waveHeadcutFactor);
            const tF =
              RHO *
              G *
              hF *
              (1 +
                0.15 * Math.min(1, Math.sqrt(Math.max(reservoirHead, 0) / Math.max(Hb, 0.5))));
            tau = Math.max(tau, tF);
            let dx: number;
            if (hcLaw === "energy") {
              const qU = (p.Cw ?? 1.7) * Math.pow(Math.max(hEff, 0), 1.5);
              dx =
                hcC *
                Math.pow(
                  Math.max(
                    qU * (Math.max(p.crestElev - zb, 0) + Math.max(hCr, 0)),
                    0,
                  ),
                  1 / 3,
                ) *
                dt *
                ef.openRate;
              // The energy law already carries its material rate through C. Applying
              // the legacy hydrostatic rate ceiling here made both selectable laws
              // advance at the same capped speed, hiding the selected closure.
            } else {
              dx =
                fH *
                excessShear(kdS, tF, tauShell, nS) *
                dt *
                ef.openRate;
              dx = Math.min(dx, maxHeadcutRate * dt);
            }
            // Material/process retardation and a physical timescale cap prevent
            // the hydrostatic headcut from crossing a 20–30 m crest in one pulse.
            dx *= headcutRetardation;
            xHead = Math.min(C, xHead + Math.max(dx, 0));

            // The headcut face remains detachment-limited even when the open
            // breach bed is configured for transport-capacity erosion.
            let dA =
              excessShear(kdS, tau, tauShell, nS) *
              ef.openRate *
              gFrac *
              Math.max(Wb, 0.5) *
              dt;
            dA = capErosionAreaPerStep(dA, gCap, Hb, Wb, dt);
            const zbBeforeErosion = zb;
            const sh = applyVol({
              dA,
              Wb,
              zb,
              zPhi,
              h: hEff,
              baseElev: p.crestElev - 0.35 * Hb,
              crestLength: p.crestLength,
              fBed: 0.5,
              widen: ef.widen,
            });
            zb = Math.max(sh.zb, p.crestElev - 0.35 * Hb);
            if (isMoraine && (p.bankCollapseEnabled ?? true)) {
              unsupportedBankExposure = updateBankCollapseExposure(
                unsupportedBankExposure,
                zbBeforeErosion - zb,
                Number.POSITIVE_INFINITY,
              ).exposure;
            }
            Wb = sh.Wb;
            Zb = Math.max(Zb, zPhi * 0.5);
            // Geometry-based maturity is evaluated during headcut travel too;
            // crest breakthrough remains an independent longitudinal milestone.
            updateBreachDevelopment(t);
          }
          stage = "headcut";
        } else {
          if (tHc == null && hcOn) tHc = t;
          let dA = 0;
          const zbBeforeErosion = zb;
          if (usesTransportCapacity) {
            const st = openNonEq(
              openCt,
              tau,
              U,
              hEff,
              Lb,
              dt,
              nOpts,
              ef.openRate,
            );
            openCt = st.CtNew;
            lastCtStar = st.CtStar;
            dA = (st.qt * dt) / (1 - poros);
          } else {
            dA =
              excessShear(kdS, tau, tauShell, nS) *
              ef.openRate *
              Math.max(Wb, 0.5) *
              dt;
          }
          dA = capErosionAreaPerStep(dA, 0.05, Hb, Wb, dt);
          // (3) Stronger post-collapse widening: less bed share, more banks
          const sh = applyVol({
            dA,
            Wb,
            zb,
            zPhi,
            h: hEff,
            baseElev: p.baseElev,
            crestLength: p.crestLength,
            fBed: 0.35,
            widen: ef.widen * 1.25,
          });
          zb = sh.zb;
          Wb = sh.Wb;
          Zb = Math.max(Zb, zPhi * 0.55);
          if (hcOn) xHead = C;
          stage = "open";

          // Discrete bank collapse for moraine (screening)
          if (
            (p.damStructure === "moraine" ||
              p.damStructure === "ice_cored_moraine") &&
            (p.bankCollapseEnabled ?? true)
          ) {
            const triggerHeight =
              Math.max(p.bankCollapseHeightFraction ?? 0.12, 0.02) * Hb;
            const exposureState = updateBankCollapseExposure(
              unsupportedBankExposure,
              zbBeforeErosion - zb,
              triggerHeight,
            );
            unsupportedBankExposure = exposureState.exposure;
            if (exposureState.collapseHeight > 0) {
              const collapseHeight = exposureState.collapseHeight;
              const wf = Math.max(p.bankCollapseWidthFactor ?? 1.5, 0.5);
              Wb = Math.min(
                Wb + 2 * collapseHeight * wf * ef.widen,
                p.crestLength * 1.05,
              );
              warnings.push(
                `Moraine bank-collapse screening event t=${(t / 3600).toFixed(4)} h; accumulated exposure=${collapseHeight.toFixed(3)} m`,
              );
            }
          }

          updateBreachDevelopment(t);
        }
      } else if (
        WL < p.crestElev - 0.02 &&
        p.mode === "overtopping" &&
        step < 5
      ) {
        stage = "filling";
      }
    }

    const Qin =
      p.inflowSeriesEnabled && p.inflowSeries?.length
        ? interpolateInflow(p.inflowSeries, t)
        : (p.inflowM3s ?? 0);
    // Qstarter is an early-stage subset of Qbreach. Count actual routes once:
    // spillway + remaining intact crest + current breach opening.
    if (waveA && p.mode === "overtopping") {
      const standingHead = Math.max(WL - p.crestElev, 0);
      const crestFlowWidth = Math.max(p.crestLength, 0.5);
      const standingOpeningWidth = starterActive
        ? clamp(Wb + 2 * Zb * standingHead, 0, crestFlowWidth)
        : 0;
      const standingCrestFlow =
        (p.Cw ?? 1.7) *
        Math.max(crestFlowWidth - standingOpeningWidth, 0) *
        Math.pow(standingHead, 1.5);
      QwaveExcess += Math.max(Qovertopping - standingCrestFlow, 0);
    }
    const Qstorage = Math.max(p.spillwayQ, 0) + Qovertopping + Qbreach;
    V = Math.max(V + (Qin - Qstorage) * dt, 0);
    y = y0 * Math.pow(V / V0, 1 / mS);
    if (y < 0.05 && tEmp == null) tEmp = t;

    if (Qovertopping > QovertoppingPeak) { QovertoppingPeak = Qovertopping; tOvertoppingPeak = t; }
    if (Qstarter > QstarterPeak) { QstarterPeak = Qstarter; tStarterPeak = t; }
    if (Qbreach > QbreachPeak) { QbreachPeak = Qbreach; tBreachPeak = t; }
    if (Q > QtotalPeak) { QtotalPeak = Q; tTotalPeak = t; }
    // Backward-compatible Qpeak remains the maximum total outflow.
    Qpeak = QtotalPeak;
    tPeak = tTotalPeak;

    if (t >= tNextRecord - 1e-9 || t >= tMax || step === 0) {
      series.push({
        t,
        Q,
        WL,
        zb,
        Wb,
        Wtop: Wb + 2 * Zb * Math.max(WL - zb, 0),
        R,
        xHeadcut: xHead,
        tau,
        V,
        stage,
        Ct: collapsed ? openCt : pipeCt,
        CtStar: lastCtStar,
        pipeW: collapsed ? undefined : pipeW,
        pipeH: collapsed ? undefined : pipeH,
        cover: collapsed ? undefined : lastCover,
        pipeInvertZ: pipeInvert,
        roofRisk: collapsed ? undefined : lastRisk,
        Qovertopping,
        QwaveExcess,
        Qstarter,
        Qbreach,
        Qtotal: Q,
        breachDevelopmentIndex,
        streamPower,
        trueBreachActive,
      });
      tNextRecord = t + recordInterval;
    }

    // Adaptive Δt: refine near collapse, high roof risk, or rapid Q change
    let dtTarget = dtMax;
    if (collapsing) dtTarget = Math.min(dtTarget, Math.max(dtMin, dtMax * 0.25));
    if (!collapsed && lastRisk > 0.6) dtTarget = Math.min(dtTarget, Math.max(dtMin, dtMax * 0.4));
    if (step > 0 && dt > 0) {
      const dQdt = Math.abs(Q - Qprev) / dt;
      if (dQdt > 50) dtTarget = Math.min(dtTarget, Math.max(dtMin, dtMax * 0.35));
      if (dQdt > 200) dtTarget = Math.min(dtTarget, Math.max(dtMin, dtMax * 0.2));
    }
    Qprev = Q;
    dt = clamp(dtTarget, dtMin, dtMax);

    if (tEmp != null && step > 20) break;
    t += dt;
    step += 1;
    if (step > 500000) {
      warnings.push("Adaptive loop step cap reached");
      break;
    }
  }

  if (DEBUG_HEADCUT) console.log(debugRows.join("\n")); // TEMP-DEBUG
  const last = series[series.length - 1];
  return {
    series,
    Qpeak,
    tPeak,
    tCollapse: tCol,
    tHeadcutBreach: tHc,
    tEmpty: tEmp,
    finalWb: last?.Wb ?? 0,
    finalDepth: last ? p.crestElev - last.zb : 0,
    elapsedMs: performance.now() - tStart,
    warnings: [...new Set(warnings)],
    pipeInvertUsed: pipeInvert,
    engineId: "v2",
    materialClass: material,
    erodibilityClass: erod,
    QovertoppingPeak,
    tOvertoppingPeak,
    QstarterPeak,
    tStarterPeak,
    QbreachPeak,
    tBreachPeak,
    QtotalPeak,
    tTotalPeak,
    tErosionInitiation,
    tStarterNotch,
    tSignificantBreach,
    finalBreachDevelopmentIndex: breachDevelopmentIndex,
    empiricalResults: buildEmpiricalResults(
      p,
      series,
      last ? Math.max(p.crestElev - last.zb, 0) : 0,
      zPhi,
    ),
  };
}

export function runBreachSimulation(p: StudioInputs): SimResult {
  return runBreachSimulationV2(p);
}


// ---- Compatibility exports for tests & Impulse panel ----

export interface TransportCapacityOpts {
  /** Sediment grain density ρs (kg/m³). */
  grainDensity: number;
  /** Median grain size D50 (m). */
  grainD50_m: number;
  /** Gradation ratio D90/D30 for the Smart (1984) factor. */
  grainD90D30Ratio: number;
  /** Critical Shields parameter θc. */
  criticalShields: number;
  /** Meyer-Peter–Müller transport coefficient Kt. */
  mpmCoefficient: number;
  /** Bed porosity p (0–1). */
  porosity: number;
  /** Erodible flow-path length Lreach (m) for the Exner conversion. */
  reachLength: number;
}

/** Dimensionless Shields stress θ = τ / ((s−1) ρ g D50). Exposed for verification. */
export function shieldsStress(tau: number, grainDensity: number, grainD50_m: number): number {
  const s_rel = Math.max(grainDensity, 1100) / RHO;
  const D50 = Math.max(grainD50_m, 1e-4);
  return tau / (Math.max(s_rel - 1, 0.1) * RHO * G * D50);
}

/**
 * Transport-capacity erosion rate [m/s] — Meyer-Peter–Müller bedload with the
 * Smart (1984) gradation factor (D90/D30)^0.2, converted to a breach-invert
 * lowering rate through Exner continuity. Cohesionless / granular material only.
 *
 *   θ  = τ / ((s−1) ρ g D50)
 *   Φ  = Kt · (D90/D30)^0.2 · max(θ − θc, 0)^1.5
 *   qs = Φ · √((s−1) g D50³)                 [m²/s per unit width]
 *   ε  = qs / ((1 − p) · Lreach)             [m/s]
 *
 * Steep-slope enhancement enters through the boundary shear τ (Manning) rather
 * than an explicit Smart S^0.6 multiplier, to avoid double-counting slope.
 * Pure and side-effect free so it can be unit-verified against hand calculation.
 */
export function mpmSmartErosionRate(tau: number, o: TransportCapacityOpts): number {
  const s_rel = Math.max(o.grainDensity, 1100) / RHO;
  const D50 = Math.max(o.grainD50_m, 1e-4);
  const gradFactor = Math.pow(Math.max(o.grainD90D30Ratio, 1), 0.2);
  const thetaC = clamp(o.criticalShields, 0.01, 0.2);
  const Kt = clamp(o.mpmCoefficient, 1, 16);
  const poros = clamp(o.porosity, 0.1, 0.6);
  const Lreach = Math.max(o.reachLength, 1);
  const theta = tau / (Math.max(s_rel - 1, 0.1) * RHO * G * D50);
  const excess = theta - thetaC;
  if (excess <= 0) return 0;
  const phi = Kt * gradFactor * Math.pow(excess, 1.5);
  const qs = phi * Math.sqrt(Math.max(s_rel - 1, 0.1) * G * D50 * D50 * D50); // m²/s
  return qs / ((1 - poros) * Lreach); // m/s
}

/**
 * Mechanistic breach-formation engine (physics v2).
 *
 * Hydraulics
 *   Open breach:  Q = Cw · Wavg · h^1.5     (averaged-width simplification of a
 *                 broad-crested trapezoidal weir — NOT the rigorous compound
 *                 trapezoidal-weir formula; adequate for screening, not a
 *                 substitute for a full compound-section rating.)
 *   Piping:       Q = Cd · π R² √(2 g H)     (orifice)
 *
 * Erosion (excess-shear form, inspired by Wan & Fell's erodibility framework)
 *   Ce = 10^(−I)                            (erosion-rate index → erodibility coefficient)
 *   ε  = (Ce / ρd) · max(τ − τc, 0)^n       [m/s]
 *   NOTE: kd = Ce/ρd does not dimensionally reduce to Wan & Fell's own erosion-rate
 *   coefficient units, and this is not their literal published regression — treat
 *   as a screening-level erodibility relationship in the same spirit, not a citation
 *   of the exact Wan & Fell (2004) equation.
 *   Exponent n (erosionExponent / shellErosionExponent, default 1): same formula
 *   family, material-dependent exponent — n=1 cohesive/fine (unchanged default),
 *   n≈1.3 cohesionless sand/gravel (Chen & Anderson 1986), n≈1.5 MPM-style
 *   transport-capacity scaling (NWS BREACH lineage).
 *
 * Moraine bank mass-wasting (moraine / ice_cored_moraine only)
 *   Smooth excess-shear widening alone under-widens moraine breach channels.
 *   Accumulates invert lowering since the prior event; once it reaches
 *   bankCollapseHeightFraction·Hb, triggers a discrete Wb widening event
 *   (bankCollapseWidthFactor), then resets. Screening proxy for the
 *   fluvial + geotechnical bank-collapse coupling in Westoby et al. (2014,
 *   HR-BREACH), validated against Dig Tsho — not a limit-equilibrium solver.
 *
 * Bed shear (open channel, Manning)
 *   τ = ρ g n² U² / Rh^(1/3)
 *
 * Pipe wall shear (Bonelli-type driving pressure)
 *   τ = ρ g R H / (2 L)
 *
 * Headcut (overtopping, Temple / WinDAM-style)
 *   Initiate when overtopping head ≥ h_init
 *   Face shear ≈ ρ g h (hydrostatic on the vertical scarp)
 *   dx/dt = f_h · ε(τ_face)   through crest width C
 *   Deepening is limited until the headcut breaches the upstream crest edge
 *
 * Geotechnics
 *   Residual side slope cannot be steeper than the friction angle:
 *   Zb ≥ cot(φ)
 *
 * Reservoir
 *   V(y) = V0 (y / y0)^m
 *   dV/dt = Qin − Q
 */

/**
 * Transient crest head from a wave-overtopping pulse train (opt-in GLOF wave→breach forcing).
 * A displacement / impulse wave rides over the crest as a half-sine pulse of peak depth `d0`
 * and duration `tO`, optionally repeated `count` times spaced `period` apart. `period ≤ 0` ⇒
 * `period = tO` (back-to-back pulses). Returns 0 outside every pulse window, and 0 whenever
 * `d0 ≤ 0` or `tO ≤ 0`. Pure function of time so it can be hand-verified in isolation; the engine
 * adds this to the transient hydraulic head. It adds no storage volume itself; outflow generated
 * by the pulse is debited once from reservoir storage.
 */
export function waveOvertopHead(
  tSec: number,
  o: { d0: number; tO: number; count: number; period: number },
): number {
  if (!(o.d0 > 0) || !(o.tO > 0)) return 0;
  const period = o.period > 0 ? o.period : o.tO;
  const count = Math.max(1, Math.round(o.count));
  for (let k = 0; k < count; k++) {
    const ts = k * period;
    if (tSec >= ts && tSec <= ts + o.tO) {
      // Half-sine envelope 0 → d0 → 0 across the overtopping duration of each pulse.
      return o.d0 * Math.sin((Math.PI * (tSec - ts)) / o.tO);
    }
  }
  return 0;
}

/**
 * WinDAM / USDA-SITES energy-dissipation headcut migration: dX/dt = C·(q·H)^(1/3).
 * `qUnit` = unit overfall discharge [m²/s], `Hdrop` = headcut drop height [m], `C`
 * (headcutEnergyCoeff) = material headcut erodibility. Returns the advance ΔX over one step `dt`
 * (never negative). Pure so the cube-root law can be hand-verified independently of the engine.
 */
export function energyHeadcutAdvance(C: number, qUnit: number, Hdrop: number, dt: number): number {
  return Math.max(C, 0) * Math.cbrt(Math.max(qUnit * Hdrop, 0)) * dt;
}

/** Inputs to the one-time avalanche displaced-volume step (Archimedes, at wave-forcing handoff). */
export interface AvalancheDisplacementInputs {
  /** Avalanche / ice-slide bulk volume [m³] (the same slideVolume fed to the Impulse module). */
  slideVolume: number;
  /** Fraction (0–1) of that bulk volume treated as submerged. Use StudioInputs.avalancheSubmergedFraction. */
  submergedFraction: number;
  /** Lake volume BEFORE displacement [m³]. */
  volumeM3: number;
  /** Lake water-surface elevation BEFORE displacement [m]. */
  initialWL: number;
  baseElev: number;
  /** Reservoir stage-storage exponent m in V(y) = V0·(y/y0)^m — same value the breach engine uses. */
  storageExponent: number;
}

export interface AvalancheDisplacementResult {
  /** Submerged bulk volume added to the lake [m³]. */
  displacedVolumeM3: number;
  /** Lake volume AFTER displacement [m³] — feed into StudioInputs.volumeM3. */
  newVolumeM3: number;
  /** Lake water-surface elevation AFTER displacement [m] — feed into StudioInputs.initialWL. */
  newInitialWL: number;
  /** Rise in water-surface elevation caused by the displacement alone [m]. */
  deltaWL: number;
}

/**
 * ONE-TIME Archimedes displaced-volume step for an avalanche/ice slide entering a lake.
 *
 * Physically distinct from — and applied BEFORE — the transient wave-overtopping forcing
 * (waveForcingEnabled): the slide mass permanently occupies volume in the lake (like dropping a
 * rock in a full glass — the water level rises and STAYS risen). The transient wave adds no
 * storage volume, while any computed wave-driven discharge is debited once as outflow.
 * Conflating the two — as the legacy "pass to breach" handoff did by injecting the wave as fake
 * inflowM3s/inflowSeries — double-counts water that was never added to the lake and skips the
 * water that actually was.
 *
 *   Vdisplaced = slideVolume · submergedFraction
 *   V_new      = V0 + Vdisplaced
 *   y_new      = y0 · (V_new / V0)^(1/m)         (inverting the SAME power-law stage-storage
 *                                                  curve V(y) = V0·(y/y0)^m used everywhere else
 *                                                  in the engine — no separate/ad hoc geometry)
 *
 * Pure and side-effect free so it can be unit-verified independently of the breach engine.
 */
export function applyAvalancheDisplacement(o: AvalancheDisplacementInputs): AvalancheDisplacementResult {
  const y0 = Math.max(o.initialWL - o.baseElev, 0.05);
  const V0 = Math.max(o.volumeM3, 1);
  const m = clamp(o.storageExponent, 1.2, 3.5);
  const displaced = Math.max(o.slideVolume, 0) * clamp(o.submergedFraction, 0, 1);
  const newVolume = V0 + displaced;
  const newY = y0 * Math.pow(newVolume / V0, 1 / m);
  const newWL = o.baseElev + newY;
  return {
    displacedVolumeM3: displaced,
    newVolumeM3: newVolume,
    newInitialWL: newWL,
    deltaWL: newWL - o.initialWL,
  };
}


export function resultToCsv(result: SimResult): string {
  const header =
    "t_s,t_hr,Q_m3s,Q_overtopping_m3s,Q_wave_excess_m3s,Q_pre_maturity_subset_m3s,Q_breach_opening_m3s,BDI,streamPower_Wm2,WL_m,zb_m,Wb_m,Wtop_m,R_m,xHeadcut_m,tau_Pa,V_m3,stage";
  const rows = result.series.map((s) =>
    [
      s.t.toFixed(1),
      (s.t / 3600).toFixed(5),
      s.Q.toFixed(4),
      (s.Qovertopping ?? 0).toFixed(4),
      (s.QwaveExcess ?? 0).toFixed(4),
      (s.Qstarter ?? 0).toFixed(4),
      (s.Qbreach ?? 0).toFixed(4),
      (s.breachDevelopmentIndex ?? 0).toFixed(4),
      (s.streamPower ?? 0).toFixed(3),
      s.WL.toFixed(4),
      s.zb.toFixed(4),
      s.Wb.toFixed(4),
      s.Wtop.toFixed(4),
      s.R.toFixed(4),
      (s.xHeadcut ?? 0).toFixed(4),
      s.tau.toFixed(3),
      s.V.toFixed(2),
      s.stage,
    ].join(","),
  );
  return [header, ...rows].join("\n");
}
