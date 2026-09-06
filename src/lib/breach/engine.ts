import type { BreachStage, SimResult, SimStep, StudioInputs } from "./types";
import { interpolateInflow } from "./inflowSeries.ts";

const G = 9.81;
const RHO = 1000;

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}

/** cm³/(N·s) → m³/(N·s) for JET-measured erodibility. */
const KD_CM3_TO_SI = 1e-6;

/**
 * Excess-shear erodibility coefficient kd, by provenance.
 *  - "index":  kd = 10^(−I)/ρd — legacy Wan & Fell-style index (dimensionally lumped;
 *              unchanged default behaviour).
 *  - "hanson": kd = 2e-7·τc^(−0.5) [m³/(N·s)] — Hanson & Simon (2001) JET regression
 *              (published as kd[cm³/N·s] = 0.2·τc^(−0.5), converted to SI). Linear (n=1).
 *  - "direct": user-measured JET value entered in cm³/(N·s), converted to SI. Linear (n=1).
 */
export function kdForMode(
  mode: "index" | "hanson" | "direct",
  I: number,
  tauCrit: number,
  rhoD: number,
  kdDirect: number,
): number {
  switch (mode) {
    case "hanson":
      return 2e-7 * Math.pow(Math.max(tauCrit, 0.1), -0.5);
    case "direct":
      return Math.max(kdDirect, 0) * KD_CM3_TO_SI;
    case "index":
    default:
      return Math.pow(10, -I) / Math.max(rhoD, 200);
  }
}

/** Inputs to the transport-capacity closure (all sourced from StudioInputs + geometry). */
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
 *   Tracks exposed unsupported bank height as the invert deepens; once it
 *   exceeds bankCollapseHeightFraction·Hb, triggers a discrete Wb widening
 *   event (bankCollapseWidthFactor), then resets. Screening proxy for the
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
 * adds this to the EROSION head only (never to reservoir storage).
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

export function runBreachSimulation(p: StudioInputs): SimResult {
  const t0 = performance.now();
  const warnings: string[] = [];
  const dt = Math.max(p.dt, 0.2);
  const tMax = Math.max(p.tMaxHours, 0.1) * 3600;
  const nSteps = Math.ceil(tMax / dt);
  const recordEvery = Math.max(1, Math.round(nSteps / 600));

  const Hb = p.crestElev - p.baseElev;
  if (Hb <= 0) {
    return emptyResult(t0, ["Dam height must be positive (crest > base)."]);
  }

  const y0 = Math.max(p.initialWL - p.baseElev, 0.05);
  const V0 = Math.max(p.volumeM3, 1);
  const m = clamp(p.storageExponent, 1.2, 3.5);
  const volumeFromY = (yy: number) => V0 * Math.pow(Math.max(yy, 0) / y0, m);
  const yFromVolume = (vol: number) => y0 * Math.pow(Math.max(vol, 0) / V0, 1 / m);

  // Homogeneous: one I. Zoned: core I for piping; shell I for open-breach / overtopping erosion.
  const I_core = p.erosionIndexI;
  const I_shell = p.damStructure === "zoned" ? (p.shellErosionIndexI ?? p.erosionIndexI) : p.erosionIndexI;
  const tauC_shell = p.damStructure === "zoned" ? (p.shellTauC ?? p.tauC) : p.tauC;

  // Excess-shear erodibility kd by provenance (kdMode). Core uses τc; shell uses τc_shell
  // (matters for the Hanson kd = 2e-7·τc^(−0.5) form). Default "index" is unchanged.
  const kdMode = p.kdMode ?? "index";
  const kd_core = kdForMode(kdMode, I_core, p.tauC, p.rhoD, p.kdDirect);
  const kd_shell = kdForMode(kdMode, I_shell, tauC_shell, p.rhoD, p.kdDirect);
  let kd = kd_core;

  // Excess-shear exponent n: ε = kd·(τ−τc)^n. n=1 (default) reproduces the
  // original linear Wan & Fell-style law exactly. n>1 (~1.3 cohesionless
  // sand/gravel, ~1.5 MPM-style transport capacity) is a screening dial for
  // more granular material — same formula family, sourced exponent range,
  // not a separate erosion law. Hanson/direct kd are linear-detachment
  // coefficients, so they pin n = 1 regardless of the exponent inputs.
  const linearKd = kdMode === "hanson" || kdMode === "direct";
  const n_core = linearKd ? 1 : clamp(p.erosionExponent ?? 1, 0.8, 1.6);
  const n_shell = linearKd
    ? 1
    : p.damStructure === "zoned"
      ? clamp(p.shellErosionExponent ?? 1, 0.8, 1.6)
      : n_core;
  let n = n_core;
  const erosionRate = (kdLocal: number, tau: number, tauCrit: number, nLocal: number) =>
    kdLocal * Math.pow(Math.max(tau - tauCrit, 0), nLocal);

  const C = Math.max(p.crestWidth, 0.5);
  const headcutOn = p.mode === "overtopping" && (p.headcutEnabled !== false);
  const fH = clamp(p.headcutAdvanceFactor ?? 6, 0.5, 40);
  const hInit = Math.max(p.headcutInitDepth ?? 0.04, 0.01);

  // ——— Headcut migration law (selectable) ———
  //   "hydrostatic" (default): legacy Temple-style dxh/dt = fh·ε(τ_face), τ_face ≈ ρg·h_face.
  //   "energy": WinDAM / USDA-SITES energy-dissipation law dX/dt = C·(q·H)^(1/3), where q is the
  //   unit overfall discharge [m²/s] and H the drop height (crest-to-invert + approach head). C
  //   (headcutEnergyCoeff) is a material headcut-erodibility, tie-able to the same JET anchor as kd.
  const headcutLaw = p.headcutLaw ?? "hydrostatic";
  const headcutC = Math.max(p.headcutEnergyCoeff ?? 0.5, 0);
  // Deepening-gate throttles — exposed so the gate can be re-examined; defaults reproduce legacy.
  const gateFrac = clamp(p.headcutGateDeepenFraction ?? 0.25, 0.05, 1);
  const gateCap = clamp(p.headcutGateDeepenCap ?? 0.015, 0.005, 0.1);

  // ——— Wave-overtopping transient forcing (opt-in GLOF wave→breach chain) ———
  // A displacement/impulse wave rides over the crest as a short pulse of peak depth d0 for
  // duration tO (optionally a train of waveCount pulses spaced by wavePeriod). It supplies the
  // EROSIVE head that initiates incision when the still pool sits at/near the crest with little
  // freeboard (moraine-GLOF trigger). Added to the erosion hydraulics ONLY — not to reservoir
  // volume, since a surface surge does not fill the lake; the mass balance keeps the real head.
  // Off by default → the loop below is byte-identical to the pre-wave engine.
  const waveOn = p.mode === "overtopping" && p.waveForcingEnabled === true;
  const waveD0 = Math.max(p.waveOvertopDepth ?? 0, 0);
  const waveTO = Math.max(p.waveOvertopDuration ?? 0, 0);
  const waveCount = clamp(Math.round(p.waveOvertopCount ?? 1), 1, 20);
  const wavePeriod = (p.waveOvertopPeriod ?? 0) > 0 ? p.waveOvertopPeriod : waveTO;
  const waveActive = waveOn && waveD0 > 0 && waveTO > 0;
  const waveOpts = { d0: waveD0, tO: waveTO, count: waveCount, period: wavePeriod };

  // ——— Transport-capacity closure (Meyer-Peter–Müller + Smart 1984 gradation) ———
  // Sediment-transport-limited erosion for cohesionless / granular / moraine material
  // (NWS BREACH lineage). Applied ONLY to open-breach deepening & widening when
  // erosionModel = "transport_capacity"; piping and the headcut face stay excess-shear.
  //   θ  = τ / ((s−1) ρ g D50)                    Shields stress
  //   Φ  = Kt · (D90/D30)^0.2 · (θ − θc)^1.5       dimensionless bedload (Smart gradation)
  //   qs = Φ · √((s−1) g D50³)                     volumetric bedload per unit width [m²/s]
  //   ε  = qs / ((1 − p) · Lreach)                 Exner continuity → invert rate [m/s]
  // Assumptions (documented): clear-water reservoir inflow (capacity fully sourced by the
  // breach), and the steep-slope enhancement enters through the boundary shear τ (Manning)
  // rather than an explicit Smart S^0.6 factor — avoids double-counting slope.
  const useTransport = p.erosionModel === "transport_capacity";
  const tcOpts: TransportCapacityOpts = {
    grainDensity: p.grainDensity ?? 2650,
    grainD50_m: p.grainD50_m ?? 0.03,
    grainD90D30Ratio: p.grainD90D30Ratio ?? 8,
    criticalShields: p.criticalShields ?? 0.047,
    mpmCoefficient: p.mpmCoefficient ?? 8,
    porosity: p.porosity ?? 0.35,
    // Erodible flow-path length Lreach = crest width + downstream-face slope length.
    reachLength: Math.max(C + Hb * Math.sqrt(1 + p.zDown * p.zDown), 1),
  };

  let y = y0;
  let V = volumeFromY(y);
  let zb = p.mode === "piping" ? p.pipeInvert : p.crestElev - 0.02;
  let Wb = p.mode === "piping" ? 0 : Math.max(p.initialNotchWidth, 0.2);
  let R = Math.max(p.initialPipeRadius, 0.02);
  let Zb = Math.max(p.zb, 0.05);
  let xHeadcut = 0;
  let headcutActive = false;
  let bankExposed = 0;
  let bankCollapseEvents = 0;
  let collapsed = p.mode === "overtopping";
  let tCollapse: number | null = p.mode === "overtopping" ? 0 : null;
  let tHeadcutBreach: number | null = headcutOn ? null : 0;
  let tEmpty: number | null = null;

  const phiRad = (p.phiDeg * Math.PI) / 180;
  const zPhi = 1 / Math.tan(Math.max(phiRad, 0.15));

  const series: SimStep[] = [];
  let Qpeak = 0;
  let tPeak = 0;

  if (p.mode === "overtopping" && p.initialWL < p.crestElev) {
    warnings.push("Initial water level is below the crest — overtopping waits until the pool rises.");
  }
  if (kdMode === "index" && p.erosionIndexI < 1.5) {
    warnings.push("Very low erosion-rate index (I < 1.5): enlargement will be extremely rapid.");
  }
  if (kdMode === "index" && p.erosionIndexI > 5.5) {
    warnings.push("Very high erosion-rate index (I > 5.5): the breach may barely grow within the run window.");
  }
  if (useTransport) {
    warnings.push(
      `Open-breach erosion: transport-capacity (Meyer-Peter–Müller / Smart) with D50 = ${(p.grainD50_m ?? 0.03).toFixed(3)} m, θc = ${p.criticalShields ?? 0.047}. Piping / headcut face remain excess-shear.`,
    );
  }
  if (kdMode === "hanson") {
    warnings.push("Erodibility kd re-anchored to Hanson & Simon (2001) JET regression kd = 0.2·τc^(−0.5) cm³/(N·s); erosion exponent pinned to n = 1.");
  }
  if (kdMode === "direct") {
    warnings.push("Erodibility kd taken directly from a measured JET value (cm³/(N·s)); erosion exponent pinned to n = 1.");
  }
  if (headcutOn) {
    warnings.push("Headcut module on: deepening is limited until the headcut migrates through the crest width C.");
  }
  if (headcutOn && headcutLaw === "energy") {
    warnings.push(
      `Headcut law: WinDAM/SITES energy dX/dt = C·(q·H)^(1/3), C = ${headcutC}; deepening-gate fraction ${gateFrac}, cap ${gateCap}·Hb.`,
    );
  }
  if (p.waveForcingEnabled === true && p.mode !== "overtopping") {
    warnings.push("Wave-overtopping forcing applies only in overtopping mode — ignored for piping.");
  }
  if (waveOn && (waveD0 <= 0 || waveTO <= 0)) {
    warnings.push(
      "Wave-overtopping forcing is enabled but overtopping depth/duration are zero — no wave head applied (run the Impulse module and pass its run-up d0 / tO).",
    );
  }
  if (waveActive) {
    warnings.push(
      `Wave-overtopping forcing on: transient crest head, peak d0 = ${waveD0.toFixed(2)} m over tO = ${waveTO.toFixed(0)} s${waveCount > 1 ? ` × ${waveCount} pulses` : ""}. Drives erosion only, not reservoir volume.`,
    );
  }

  for (let i = 0; i <= nSteps; i++) {
    const t = i * dt;
    const WL = p.baseElev + y;
    let Q = Math.max(p.spillwayQ, 0);
    let tau = 0;
    let stage: BreachStage = collapsed ? "open" : "piping";
    const tauCrit = collapsed ? tauC_shell : p.tauC;

    // —— Piping branch (core material) ——
    if (!collapsed) {
      kd = kd_core;
      n = n_core;
      const Hpipe = Math.max(WL - p.pipeInvert, 0);
      if (Hpipe > 0) {
        const area = Math.PI * R * R;
        Q += p.CdOrifice * area * Math.sqrt(2 * G * Hpipe);
        const pressurized = 2 * R < Hpipe;
        if (pressurized) {
          tau = (RHO * G * R * Hpipe) / (2 * Math.max(p.coreLength, 0.5));
        } else {
          const RhFreeSurface = Hpipe / 4;
          const Sf = Hpipe / Math.max(p.coreLength, 0.5);
          tau = RHO * G * RhFreeSurface * Sf;
        }
        R += erosionRate(kd, tau, p.tauC, n) * dt;
        const cover = Math.max(p.crestElev - p.pipeInvert, 0.2);
        if (2 * R >= p.collapseRatio * cover) {
          collapsed = true;
          tCollapse = t;
          Wb = Math.max(2 * R, p.initialNotchWidth);
          zb = clamp(p.pipeInvert - R, p.baseElev, p.crestElev);
          xHeadcut = C;
          tHeadcutBreach = t;
          stage = "open";
        }
      } else {
        stage = "filling";
      }
    }

    // —— Open / overtopping branch (shell if zoned) ——
    if (collapsed) {
      kd = kd_shell;
      n = n_shell;
      const tauCrit = tauC_shell;
      const waveHead = waveActive ? waveOvertopHead(t, waveOpts) : 0;
      const h = Math.max(WL - zb, 0);
      const hEff = h + waveHead; // erosive flow depth incl. the transient wave overtopping
      const hCrest = Math.max(WL - p.crestElev, 0) + waveHead;

      if (hEff > 1e-4 && WL + waveHead >= zb) {
        // Reservoir drainage uses the REAL standing head (the wave is a surface surge, not
        // stored volume) — only the erosive hydraulics below see the wave-augmented depth.
        const Wavg = Wb + Zb * h;
        const qWeir = p.Cw * Wavg * Math.pow(h, 1.5);
        Q += qWeir;

        // Erosive hydraulics on the effective (wave-augmented) flow depth hEff. With no wave
        // (waveHead = 0) hEff = h and every quantity below reduces to the legacy value.
        const A = Math.max(hEff * (Wb + Zb * hEff), 1e-6);
        const Pw = Wb + 2 * hEff * Math.sqrt(1 + Zb * Zb);
        const Rh = A / Math.max(Pw, 1e-6);
        const qErode = p.Cw * (Wb + Zb * hEff) * Math.pow(hEff, 1.5);
        const U = qErode / A;
        const tauBed =
          (RHO * G * p.manningN * p.manningN * U * U) / Math.pow(Math.max(Rh, 0.03), 1 / 3);

        // Residual side-slope: cannot stand steeper than φ
        if (Zb < zPhi * 0.95) {
          Zb = zPhi;
        }

        const headcutComplete = !headcutOn || xHeadcut >= C - 1e-6;

        if (headcutOn && !headcutComplete) {
          // Initiate discrete headcut once overtopping head is meaningful
          if (!headcutActive && hCrest >= hInit) {
            headcutActive = true;
          }

          if (headcutActive || hCrest >= hInit) {
            headcutActive = true;
            // Hydrostatic face shear + mild dynamic factor (screening upgrade of pure ρgh).
            // hFace uses the effective (wave-augmented) depth so a wave-overtopping pulse can
            // drive the scarp even when the still pool sits right at the crest.
            const hFace = Math.max(hCrest, hEff * 0.35);
            const FrScale = Math.min(1.2, Math.sqrt(Math.max(hCrest, 0) / Math.max(C, 0.5)));
            const tauFace = RHO * G * hFace * (1 + 0.25 * FrScale);
            tau = Math.max(tauBed, tauFace);
            const erFace = erosionRate(kd, tauFace, tauCrit, n);
            // Horizontal scarp advance — selectable law.
            let dx: number;
            if (headcutLaw === "energy") {
              // WinDAM / USDA-SITES energy dissipation: dX/dt = C·(q·H)^(1/3).
              //   q = unit overfall discharge [m²/s] (broad-crested weir per unit width),
              //   H = drop height = crest-to-invert geometric drop + approach head over the crest.
              const qUnit = p.Cw * Math.pow(Math.max(hEff, 0), 1.5);
              const Hdrop = Math.max(p.crestElev - zb, 0) + Math.max(hCrest, 0);
              dx = energyHeadcutAdvance(headcutC, qUnit, Hdrop, dt);
            } else {
              dx = fH * erFace * dt;
            }
            xHeadcut = Math.min(C, xHeadcut + dx);

            // Limited scarp lowering while the headcut is still in the crest (the deepening
            // "gate"). gateFrac / gateCap default to the legacy 0.25 and 0.015·Hb.
            const erLimited = erosionRate(kd, tauBed, tauCrit, n) * gateFrac;
            const dz = Math.min(erLimited * dt, gateCap * Hb);
            zb = Math.max(zb - dz, p.crestElev - 0.35 * Hb);
            Wb = Math.min(Wb + 2 * erFace * p.sideErosionFactor * 0.5 * dt, p.crestLength * 1.05);
            stage = "headcut";

            if (xHeadcut >= C - 1e-6 && tHeadcutBreach == null) {
              tHeadcutBreach = t;
              const zbBefore = zb;
              // Drop invert once the crest is fully cut through
              zb = Math.min(zb, p.crestElev - 0.15 * Hb);
              // Moraine: this sudden invert drop undercuts the banks by the same
              // amount — it IS a bank-collapse event, not a separate later one.
              // Fold the drop straight into bankExposed instead of leaving it to
              // accumulate from a still-narrow channel (which arrives too late
              // to matter for Qpeak).
              const bankCollapseOnBreach =
                (p.damStructure === "moraine" || p.damStructure === "ice_cored_moraine") &&
                (p.bankCollapseEnabled ?? true);
              if (bankCollapseOnBreach) {
                bankExposed += Math.max(zbBefore - zb, 0);
                const collapseTrigger = Math.max(p.bankCollapseHeightFraction ?? 0.12, 0.02) * Hb;
                if (bankExposed >= collapseTrigger) {
                  const widthFactor = Math.max(p.bankCollapseWidthFactor ?? 1.5, 0.5);
                  Wb = Math.min(Wb + 2 * bankExposed * widthFactor, p.crestLength * 1.05);
                  bankCollapseEvents += 1;
                  bankExposed = 0;
                }
              }
            }
          } else {
            tau = tauBed;
            stage = hCrest > 0 ? "open" : "filling";
          }
        } else {
          // Full open-channel erosion after headcut breach (or when module is off).
          // Erosion closure: transport-capacity (MPM/Smart → Exner) for granular material,
          // else detachment-limited excess-shear. Both return an invert-lowering rate [m/s].
          tau = tauBed;
          const er = useTransport
            ? mpmSmartErosionRate(tauBed, tcOpts)
            : erosionRate(kd, tauBed, tauCrit, n);
          const dz = Math.min(er * dt, 0.04 * Hb);
          zb = Math.max(zb - dz, p.baseElev);
          Wb = Math.min(Wb + 2 * er * p.sideErosionFactor * dt, p.crestLength * 1.05);
          Zb = Math.max(Zb, zPhi * 0.45);
          if (headcutOn) xHeadcut = C;
          stage = "open";

          // —— Moraine / ice-cored moraine: discrete bank mass-wasting ——
          // Fluvial erosion (above) alone under-widens moraine channels; real
          // moraine breaches widen via periodic bank collapse as undercutting
          // exposes more bank height than the material can stand unsupported
          // (Westoby et al. 2014, HR-BREACH — validated against Dig Tsho).
          const bankCollapseOn =
            (p.damStructure === "moraine" || p.damStructure === "ice_cored_moraine") &&
            (p.bankCollapseEnabled ?? true);
          if (bankCollapseOn) {
            bankExposed += dz;
            const collapseTrigger = Math.max(p.bankCollapseHeightFraction ?? 0.12, 0.02) * Hb;
            if (bankExposed >= collapseTrigger) {
              const widthFactor = Math.max(p.bankCollapseWidthFactor ?? 1.5, 0.5);
              Wb = Math.min(Wb + 2 * bankExposed * widthFactor, p.crestLength * 1.05);
              bankCollapseEvents += 1;
              bankExposed = 0;
            }
          }
        }
      } else if (WL < p.crestElev - 0.02 && p.mode === "overtopping" && i < 3) {
        stage = "filling";
      }
    }

    // Inflow: discrete hydrograph Q_in(t) when enabled, else constant inflowM3s
    const Qin =
      p.inflowSeriesEnabled && p.inflowSeries && p.inflowSeries.length > 0
        ? interpolateInflow(p.inflowSeries, t)
        : p.inflowM3s;
    const dV = (Qin - Q) * dt;
    if (V + dV < 0) {
      Q = V / dt + Qin;
      V = 0;
    } else {
      V = V + dV;
    }
    y = yFromVolume(V);
    if (y > Hb + 8) {
      y = Hb + 8;
      V = volumeFromY(y);
      warnings.push("Pool rose more than 8 m above the crest — check inflow versus spillway capacity.");
    }

    if (Q > Qpeak) {
      Qpeak = Q;
      tPeak = t;
    }

    const hNow = Math.max(p.baseElev + y - zb, 0);
    const Wtop = Wb + 2 * Zb * hNow;
    const step: SimStep = {
      t,
      Q: Math.max(Q, 0),
      WL: p.baseElev + y,
      zb,
      Wb,
      Wtop,
      R,
      xHeadcut,
      tau,
      V,
      stage,
    };

    if (i % recordEvery === 0 || i === nSteps) series.push(step);

    if (V <= 0.002 * V0 && Q < 0.02 * Math.max(Qpeak, 1) && t > 30) {
      tEmpty = t;
      step.stage = "empty";
      if (series[series.length - 1] !== step) series.push(step);
      break;
    }
  }

  if (bankCollapseEvents > 0) {
    warnings.push(
      `Moraine bank-collapse module: ${bankCollapseEvents} discrete widening event(s) triggered during open-breach erosion.`,
    );
  }

  const last = series[series.length - 1];
  return {
    series,
    Qpeak,
    tPeak,
    tCollapse,
    tHeadcutBreach,
    tEmpty,
    finalWb: last?.Wb ?? 0,
    finalDepth: last ? p.crestElev - last.zb : 0,
    elapsedMs: performance.now() - t0,
    warnings: [...new Set(warnings)],
  };
}

function emptyResult(t0: number, warnings: string[]): SimResult {
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
    warnings,
  };
}

export function resultToCsv(result: SimResult): string {
  const header =
    "t_s,t_hr,Q_m3s,WL_m,zb_m,Wb_m,Wtop_m,R_m,xHeadcut_m,tau_Pa,V_m3,stage";
  const rows = result.series.map((s) =>
    [
      s.t.toFixed(1),
      (s.t / 3600).toFixed(5),
      s.Q.toFixed(4),
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
