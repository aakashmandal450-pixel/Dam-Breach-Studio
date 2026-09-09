/**
 * Dig Tsho 1985 — full chain validation:
 *   ice avalanche → impulse wave (2D + 3D) → run-up/overtopping → pass to breach → Qpeak
 *
 * Usage:
 *   npm run validate:case -- validation/cases/run_digtsho_impulse_breach.ts
 *   (or: npx jiti validation/cases/run_digtsho_impulse_breach.ts)
 *
 * Published targets (Vuichard & Zimmermann 1987):
 *   wave height ≈ 4.4–5 m
 *   peak discharge ≈ 1600 m³/s (range ~1375–2000)
 */
import { DEFAULT_INPUTS, type StudioInputs } from "../../src/lib/breach/types.ts";
import { runBreachSimulation } from "../../src/lib/breach/engine.ts";
import { pulseHydrograph } from "../../src/lib/breach/inflowSeries.ts";
import { computeImpulse2D } from "../../src/lib/impulse/gen2d.ts";
import { computeImpulse3D } from "../../src/lib/impulse/gen3d.ts";
import { computeRunup } from "../../src/lib/impulse/runup.ts";
import { impactVelocityFromFallHeight } from "../../src/lib/impulse/velocity.ts";
import type { Impulse2DInputs, Impulse3DInputs } from "../../src/lib/impulse/types.ts";

// ─── Published / screening Dig Tsho parameters ───────────────────────────────
const FALL_HEIGHT = 60; // m — screening (not published)
const VS = impactVelocityFromFallHeight(FALL_HEIGHT);

const impulse2D: Impulse2DInputs = {
  fallHeight: FALL_HEIGHT,
  Vs: VS,
  autoVelocity: true,
  slideVolume: 150_000, // m³ — Vuichard & Zimmermann
  s: 10, // m — screening thickness
  b: 200, // m — published estimate
  rhoS: 950, // kg/m³ — ice / ice-debris mix
  nPercent: 38,
  alphaDeg: 30, // avalanche path ~30°
  h: 18, // m — measured lake depth
  x: 1200, // m — distance to dam along lake (~lake length scale)
};

const impulse3D: Impulse3DInputs = {
  ...impulse2D,
  r: 1200, // m
  gammaDeg: 0, // main lobe toward outlet
};

// Dam / reservoir geometry for breach (active hydraulic height = lake depth)
const dam = {
  baseElev: 0,
  crestElev: 18, // active water-column height
  crestWidth: 25,
  crestLength: 220,
  zDown: 2.5,
  initialWL: 18, // full to rim (freeboard ≈ 0)
  volumeM3: 5_500_000,
};

const PUBLISHED_WAVE_H = 5.0; // m (they also cite 4.4 m from Huber formula)
const PUBLISHED_WAVE_H_RANGE: [number, number] = [4.4, 9.0];
const PUBLISHED_QPEAK = 1600; // m³/s
const PUBLISHED_QPEAK_RANGE: [number, number] = [1375, 2000];

function pctError(sim: number, obs: number): string {
  if (obs === 0) return "n/a";
  const e = ((sim - obs) / obs) * 100;
  return `${e >= 0 ? "+" : ""}${e.toFixed(1)}%`;
}

function passToBreach(
  a: number,
  H: number,
  h: number,
  T: number,
  freeboard: number,
  betaDeg: number,
  crestWidth: number,
  crestLength: number,
  crestElev: number,
  baseInputs: StudioInputs,
): { inputs: StudioInputs; runup: ReturnType<typeof computeRunup> } {
  const runup = computeRunup({ a, H, h, betaDeg, f: freeboard, bK: crestWidth, T });

  const inputs: StudioInputs = { ...baseInputs };
  inputs.mode = "overtopping";
  inputs.headcutEnabled = true;

  if (runup.overtops) {
    // Same logic as ImpulseWavePanel.passToBreach()
    const excess = Math.max(0, runup.R - freeboard);
    inputs.initialWL = crestElev + Math.min(0.15, Math.max(0.02, excess * 0.1));
    const pulseQ = runup.qm * Math.max(crestLength * 0.25, 1);
    inputs.inflowM3s = Math.max(inputs.inflowM3s, pulseQ);
    if (runup.V > 0 && runup.tO > 0) {
      const Vtot = runup.V * Math.max(crestLength * 0.25, 1);
      const series = pulseHydrograph(Vtot, runup.tO, 20);
      inputs.inflowSeries = series;
      inputs.inflowSeriesEnabled = true;
      inputs.inflowSeriesUnit = "s";
      inputs.inflowSeriesDuration = runup.tO;
      inputs.inflowSeriesInterval = Math.max(runup.tO / 20, 0.5);
    }
  }

  return { inputs, runup };
}

function main() {
  console.log("\n========================================================");
  console.log(" Dig Tsho 1985 — Impulse wave → Overtopping → Breach");
  console.log("========================================================\n");

  console.log("Published targets (Vuichard & Zimmermann 1987):");
  console.log(`  Wave height:     ~${PUBLISHED_WAVE_H} m  (range ${PUBLISHED_WAVE_H_RANGE[0]}–${PUBLISHED_WAVE_H_RANGE[1]} m)`);
  console.log(`  Peak discharge:  ~${PUBLISHED_QPEAK} m³/s (range ${PUBLISHED_QPEAK_RANGE[0]}–${PUBLISHED_QPEAK_RANGE[1]})`);
  console.log();

  console.log("--- Avalanche / lake inputs used ---");
  console.log(`  Slide volume     = ${impulse2D.slideVolume} m³`);
  console.log(`  Slide width b    = ${impulse2D.b} m`);
  console.log(`  Slide thickness s= ${impulse2D.s} m`);
  console.log(`  Density ρs       = ${impulse2D.rhoS} kg/m³`);
  console.log(`  Porosity n       = ${impulse2D.nPercent} %`);
  console.log(`  Impact angle α   = ${impulse2D.alphaDeg} °`);
  console.log(`  Lake depth h     = ${impulse2D.h} m`);
  console.log(`  Fall height      = ${FALL_HEIGHT} m  →  Vs = ${VS.toFixed(1)} m/s`);
  console.log(`  Distance to dam  = ${impulse2D.x} m (2D x / 3D r)`);
  console.log();

  // ── 2D impulse ──────────────────────────────────────────────────────────
  console.log("========== 2-D Impulse wave ==========");
  const r2 = computeImpulse2D(impulse2D);
  console.log(`  P (impulse product) = ${r2.P.toFixed(3)}`);
  console.log(`  aM (max amplitude)  = ${r2.aM.toFixed(2)} m`);
  console.log(`  HM (max height)     = ${r2.HM.toFixed(2)} m`);
  console.log(`  xM                  = ${r2.xM.toFixed(1)} m`);
  console.log(`  TM                  = ${r2.TM.toFixed(2)} s`);
  if (r2.warnings.length) console.log(`  warnings: ${r2.warnings.join("; ")}`);

  const freeboard = Math.max(0, dam.crestElev - dam.initialWL); // ≈ 0
  const betaDeg = (Math.atan(1 / Math.max(dam.zDown, 0.1)) * 180) / Math.PI;

  const chain2 = passToBreach(
    r2.aM,
    r2.HM,
    impulse2D.h,
    r2.TM,
    freeboard,
    betaDeg,
    dam.crestWidth,
    dam.crestLength,
    dam.crestElev,
    {
      ...DEFAULT_INPUTS,
      projectName: "Dig Tsho 1985 – 2D wave → breach",
      damStructure: "moraine",
      baseElev: dam.baseElev,
      crestElev: dam.crestElev,
      crestWidth: dam.crestWidth,
      crestLength: dam.crestLength,
      zDown: dam.zDown,
      zUp: 1.8,
      initialWL: dam.initialWL,
      volumeM3: dam.volumeM3,
      surfaceAreaHa: 50,
      lakeVolumeFormula: "manual",
      storageExponent: 1.8,
      inflowM3s: 5,
      erosionIndexI: 2.6,
      tauC: 4,
      rhoD: 1900,
      phiDeg: 34,
      manningN: 0.035,
      sideErosionFactor: 1.3,
      headcutEnabled: true,
      headcutInitDepth: 0.2,
      headcutAdvanceFactor: 8,
      initialNotchWidth: 5,
      Cw: 1.6,
      dt: 5,
      tMaxHours: 8,
      glofIceEnabled: true,
    },
  );

  console.log(`\n  Run-up R            = ${chain2.runup.R.toFixed(2)} m`);
  console.log(`  Freeboard f         = ${freeboard.toFixed(2)} m`);
  console.log(`  Overtops?           = ${chain2.runup.overtops ? "YES" : "NO"}`);
  console.log(`  Overtop volume V    = ${chain2.runup.V.toFixed(2)} m³/m`);
  console.log(`  Overtop duration tO = ${chain2.runup.tO.toFixed(1)} s`);
  console.log(`  Wave height error vs published ${PUBLISHED_WAVE_H} m: ${pctError(r2.HM, PUBLISHED_WAVE_H)}`);

  console.log("\n  --- Breach after Pass-to-A3 (2D wave) ---");
  const br2 = runBreachSimulation(chain2.inputs);
  console.log(`  Simulated Qpeak     = ${br2.Qpeak.toFixed(1)} m³/s`);
  console.log(`  Observed Qpeak      = ${PUBLISHED_QPEAK} m³/s (range ${PUBLISHED_QPEAK_RANGE[0]}–${PUBLISHED_QPEAK_RANGE[1]})`);
  console.log(`  Error               = ${pctError(br2.Qpeak, PUBLISHED_QPEAK)}`);
  console.log(`  t_peak              = ${(br2.tPeak / 3600).toFixed(2)} h`);
  console.log(`  Final Wb / depth    = ${br2.finalWb.toFixed(1)} m / ${br2.finalDepth.toFixed(1)} m`);
  if (br2.warnings.length) console.log(`  Engine warnings: ${br2.warnings.join("; ")}`);

  // ── 3D impulse ──────────────────────────────────────────────────────────
  console.log("\n========== 3-D Impulse wave ==========");
  const r3 = computeImpulse3D(impulse3D);
  console.log(`  P (impulse product) = ${r3.P.toFixed(3)}`);
  console.log(`  aM (rep. amplitude) = ${r3.aM.toFixed(2)} m`);
  console.log(`  HM (rep. height)    = ${r3.HM.toFixed(2)} m`);
  console.log(`  r0(γ)               = ${r3.r0Gamma?.toFixed?.(1) ?? r3.rM.toFixed(1)} m`);
  console.log(`  inside near-field?  = ${r3.insideNearField ?? "n/a"}`);
  console.log(`  TM                  = ${r3.TM.toFixed(2)} s`);
  if (r3.warnings.length) console.log(`  warnings: ${r3.warnings.join("; ")}`);

  const chain3 = passToBreach(
    r3.aM,
    r3.HM,
    impulse3D.h,
    r3.TM,
    freeboard,
    betaDeg,
    dam.crestWidth,
    dam.crestLength,
    dam.crestElev,
    {
      ...DEFAULT_INPUTS,
      projectName: "Dig Tsho 1985 – 3D wave → breach",
      damStructure: "moraine",
      baseElev: dam.baseElev,
      crestElev: dam.crestElev,
      crestWidth: dam.crestWidth,
      crestLength: dam.crestLength,
      zDown: dam.zDown,
      zUp: 1.8,
      initialWL: dam.initialWL,
      volumeM3: dam.volumeM3,
      surfaceAreaHa: 50,
      lakeVolumeFormula: "manual",
      storageExponent: 1.8,
      inflowM3s: 5,
      erosionIndexI: 2.6,
      tauC: 4,
      rhoD: 1900,
      phiDeg: 34,
      manningN: 0.035,
      sideErosionFactor: 1.3,
      headcutEnabled: true,
      headcutInitDepth: 0.2,
      headcutAdvanceFactor: 8,
      initialNotchWidth: 5,
      Cw: 1.6,
      dt: 5,
      tMaxHours: 8,
      glofIceEnabled: true,
    },
  );

  console.log(`\n  Run-up R            = ${chain3.runup.R.toFixed(2)} m`);
  console.log(`  Freeboard f         = ${freeboard.toFixed(2)} m`);
  console.log(`  Overtops?           = ${chain3.runup.overtops ? "YES" : "NO"}`);
  console.log(`  Overtop volume V    = ${chain3.runup.V.toFixed(2)} m³/m`);
  console.log(`  Overtop duration tO = ${chain3.runup.tO.toFixed(1)} s`);
  console.log(`  Wave height error vs published ${PUBLISHED_WAVE_H} m: ${pctError(r3.HM, PUBLISHED_WAVE_H)}`);

  console.log("\n  --- Breach after Pass-to-A3 (3D wave) ---");
  const br3 = runBreachSimulation(chain3.inputs);
  console.log(`  Simulated Qpeak     = ${br3.Qpeak.toFixed(1)} m³/s`);
  console.log(`  Observed Qpeak      = ${PUBLISHED_QPEAK} m³/s (range ${PUBLISHED_QPEAK_RANGE[0]}–${PUBLISHED_QPEAK_RANGE[1]})`);
  console.log(`  Error               = ${pctError(br3.Qpeak, PUBLISHED_QPEAK)}`);
  console.log(`  t_peak              = ${(br3.tPeak / 3600).toFixed(2)} h`);
  console.log(`  Final Wb / depth    = ${br3.finalWb.toFixed(1)} m / ${br3.finalDepth.toFixed(1)} m`);
  if (br3.warnings.length) console.log(`  Engine warnings: ${br3.warnings.join("; ")}`);

  // ── Summary table ───────────────────────────────────────────────────────
  console.log("\n========================================================");
  console.log(" SUMMARY  (simulated vs published)");
  console.log("========================================================");
  console.log("                  |  Simulated     |  Published      |  Error");
  console.log("------------------+----------------+-----------------+--------");
  console.log(
    `  2D wave HM       |  ${r2.HM.toFixed(2).padStart(8)} m    |  ~5 (4.4–9) m    |  ${pctError(r2.HM, PUBLISHED_WAVE_H)}`,
  );
  console.log(
    `  2D breach Qpeak  |  ${br2.Qpeak.toFixed(0).padStart(8)} m3/s |  1600 (1375–2000)|  ${pctError(br2.Qpeak, PUBLISHED_QPEAK)}`,
  );
  console.log(
    `  3D wave HM       |  ${r3.HM.toFixed(2).padStart(8)} m    |  ~5 (4.4–9) m    |  ${pctError(r3.HM, PUBLISHED_WAVE_H)}`,
  );
  console.log(
    `  3D breach Qpeak  |  ${br3.Qpeak.toFixed(0).padStart(8)} m3/s |  1600 (1375–2000)|  ${pctError(br3.Qpeak, PUBLISHED_QPEAK)}`,
  );
  console.log();
  console.log("Notes:");
  console.log("  - Fall height / Vs and slide thickness are screening values (not published).");
  console.log("  - Freeboard set to 0 (lake full to rim). Wave drives overtopping pulse into breach.");
  console.log("  - Lake bed bathymetry is still a single depth h=18 m (variable depth deferred).");
  console.log("  - Erodibility I=2.6 is a screening value for moraine till.");
  console.log();
}

main();
