import type { BreachStage, SimResult, SimStep, StudioInputs } from "./types";
import { interpolateInflow } from "./inflowSeries";

const G = 9.81;
const RHO = 1000;

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
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
 *   ε  = (Ce / ρd) · max(τ − τc, 0)         [m/s]
 *   NOTE: kd = Ce/ρd does not dimensionally reduce to Wan & Fell's own erosion-rate
 *   coefficient units, and this is not their literal published regression — treat
 *   as a screening-level erodibility relationship in the same spirit, not a citation
 *   of the exact Wan & Fell (2004) equation.
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
  const Ce_core = Math.pow(10, -I_core);
  const Ce_shell = Math.pow(10, -I_shell);
  const kd_core = Ce_core / Math.max(p.rhoD, 200);
  const kd_shell = Ce_shell / Math.max(p.rhoD, 200);
  let kd = kd_core;

  const C = Math.max(p.crestWidth, 0.5);
  const headcutOn = p.mode === "overtopping" && (p.headcutEnabled !== false);
  const fH = clamp(p.headcutAdvanceFactor ?? 6, 0.5, 40);
  const hInit = Math.max(p.headcutInitDepth ?? 0.04, 0.01);

  let y = y0;
  let V = volumeFromY(y);
  let zb = p.mode === "piping" ? p.pipeInvert : p.crestElev - 0.02;
  let Wb = p.mode === "piping" ? 0 : Math.max(p.initialNotchWidth, 0.2);
  let R = Math.max(p.initialPipeRadius, 0.02);
  let Zb = Math.max(p.zb, 0.05);
  let xHeadcut = 0;
  let headcutActive = false;
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
  if (p.erosionIndexI < 1.5) {
    warnings.push("Very low erosion-rate index (I < 1.5): enlargement will be extremely rapid.");
  }
  if (p.erosionIndexI > 5.5) {
    warnings.push("Very high erosion-rate index (I > 5.5): the breach may barely grow within the run window.");
  }
  if (headcutOn) {
    warnings.push("Headcut module on: deepening is limited until the headcut migrates through the crest width C.");
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
        R += kd * Math.max(tau - p.tauC, 0) * dt;
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
      const tauCrit = tauC_shell;
      const h = Math.max(WL - zb, 0);
      const hCrest = Math.max(WL - p.crestElev, 0);

      if (h > 1e-4 && WL >= zb) {
        const Wavg = Wb + Zb * h;
        const qWeir = p.Cw * Wavg * Math.pow(h, 1.5);
        Q += qWeir;

        const A = Math.max(h * (Wb + Zb * h), 1e-6);
        const Pw = Wb + 2 * h * Math.sqrt(1 + Zb * Zb);
        const Rh = A / Math.max(Pw, 1e-6);
        const U = qWeir / A;
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
            // Hydrostatic face stress on the vertical scarp (order-of-magnitude Temple driver)
            // Hydrostatic face shear + mild dynamic factor (screening upgrade of pure ρgh)
            const hFace = Math.max(hCrest, h * 0.35);
            const FrScale = Math.min(1.2, Math.sqrt(Math.max(hCrest, 0) / Math.max(C, 0.5)));
            const tauFace = RHO * G * hFace * (1 + 0.25 * FrScale);
            tau = Math.max(tauBed, tauFace);
            const erFace = kd * Math.max(tauFace - tauCrit, 0);
            const dx = fH * erFace * dt;
            xHeadcut = Math.min(C, xHeadcut + dx);

            // Limited scarp lowering while the headcut is still in the crest
            const erLimited = kd * Math.max(tauBed - tauCrit, 0) * 0.25;
            const dz = Math.min(erLimited * dt, 0.015 * Hb);
            zb = Math.max(zb - dz, p.crestElev - 0.35 * Hb);
            Wb = Math.min(Wb + 2 * erFace * p.sideErosionFactor * 0.5 * dt, p.crestLength * 1.05);
            stage = "headcut";

            if (xHeadcut >= C - 1e-6 && tHeadcutBreach == null) {
              tHeadcutBreach = t;
              // Drop invert once the crest is fully cut through
              zb = Math.min(zb, p.crestElev - 0.15 * Hb);
            }
          } else {
            tau = tauBed;
            stage = hCrest > 0 ? "open" : "filling";
          }
        } else {
          // Full open-channel erosion after headcut breach (or when module is off)
          tau = tauBed;
          const er = kd * Math.max(tauBed - tauCrit, 0);
          const dz = Math.min(er * dt, 0.04 * Hb);
          zb = Math.max(zb - dz, p.baseElev);
          Wb = Math.min(Wb + 2 * er * p.sideErosionFactor * dt, p.crestLength * 1.05);
          Zb = Math.max(Zb, zPhi * 0.45);
          if (headcutOn) xHeadcut = C;
          stage = "open";
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
