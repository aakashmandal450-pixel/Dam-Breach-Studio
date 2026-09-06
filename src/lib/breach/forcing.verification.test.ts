/**
 * Tier 1 verification for the wave→breach forcing chain and the WinDAM/USDA-SITES
 * energy headcut law added in improvement #2.
 *
 * "Verification" = does the TypeScript reproduce the closed-form physics for the same
 * inputs. Reference numbers are hand-derived from the governing relations
 * (half-sine overtopping pulse train h_eff = d0·sin(π(t−t_k)/tO); energy-dissipation
 * migration dX/dt = C·(q·H)^(1/3)) and re-derived in-test, so a mismatch means the code
 * drifted from the math. The engine-integration block additionally guards the reaffirmed
 * regression contract: the forcing is INERT unless explicitly opted in.
 *
 * Run: node --experimental-strip-types --test src/lib/breach/forcing.verification.test.ts
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { waveOvertopHead, energyHeadcutAdvance, runBreachSimulation } from "./engine.ts";
import { DEFAULT_INPUTS, type StudioInputs } from "./types.ts";

function assertClose(actual: number, expected: number, relTol: number, label: string): void {
  const diff = Math.abs(actual - expected);
  const tol = Math.max(Math.abs(expected) * relTol, 1e-12);
  assert.ok(diff <= tol, `${label}: got ${actual}, expected ${expected} (diff ${diff}, tol ${tol})`);
}

describe("waveOvertopHead — half-sine overtopping pulse train", () => {
  const o = { d0: 4, tO: 40, count: 1, period: 0 }; // period 0 ⇒ period = tO

  it("is zero at the pulse start (sin 0)", () => {
    assertClose(waveOvertopHead(0, o), 0, 1e-9, "h(0)");
  });

  it("peaks at exactly d0 at the pulse midpoint (sin π/2)", () => {
    // t = tO/2 = 20 → sin(π/2) = 1 → d0
    assertClose(waveOvertopHead(20, o), 4, 1e-12, "h(tO/2)");
  });

  it("matches the hand value at the quarter point (sin π/4)", () => {
    // t = 10 → sin(π/4) = 0.70710678… → 4·0.70710678 = 2.8284271247
    assertClose(waveOvertopHead(10, o), 2.8284271247461903, 1e-9, "h(tO/4)");
  });

  it("is symmetric about the midpoint", () => {
    assertClose(waveOvertopHead(10, o), waveOvertopHead(30, o), 1e-12, "symmetry h(10)=h(30)");
  });

  it("returns to zero at the pulse end (sin π)", () => {
    assertClose(waveOvertopHead(40, o), 0, 1e-9, "h(tO)");
  });

  it("is zero after a single pulse ends", () => {
    assert.equal(waveOvertopHead(40.5, o), 0, "h past single pulse");
    assert.equal(waveOvertopHead(1000, o), 0, "h long after pulse");
  });
});

describe("waveOvertopHead — multi-pulse train spacing & guards", () => {
  it("places each of N pulses at k·period with a peak of d0", () => {
    const t = { d0: 4, tO: 40, count: 3, period: 100 };
    assertClose(waveOvertopHead(20, t), 4, 1e-12, "pulse 0 mid (t=20)");
    assertClose(waveOvertopHead(120, t), 4, 1e-12, "pulse 1 mid (t=120)");
    assertClose(waveOvertopHead(220, t), 4, 1e-12, "pulse 2 mid (t=220)");
  });

  it("is zero in the gap between spaced pulses and after the last one", () => {
    const t = { d0: 4, tO: 40, count: 3, period: 100 };
    assert.equal(waveOvertopHead(70, t), 0, "gap between pulse 0 and 1");
    assert.equal(waveOvertopHead(170, t), 0, "gap between pulse 1 and 2");
    assert.equal(waveOvertopHead(400, t), 0, "after last pulse");
  });

  it("period ≤ 0 gives back-to-back pulses spaced by tO", () => {
    // count 2, period 0 ⇒ period = tO = 40 ⇒ pulse 1 occupies [40,80], mid at 60.
    const t = { d0: 4, tO: 40, count: 2, period: 0 };
    assertClose(waveOvertopHead(20, t), 4, 1e-12, "pulse 0 mid");
    assertClose(waveOvertopHead(60, t), 4, 1e-12, "pulse 1 mid (back-to-back)");
  });

  it("is identically zero for a non-positive amplitude or duration", () => {
    assert.equal(waveOvertopHead(20, { d0: 0, tO: 40, count: 1, period: 0 }), 0, "d0=0");
    assert.equal(waveOvertopHead(20, { d0: -3, tO: 40, count: 1, period: 0 }), 0, "d0<0");
    assert.equal(waveOvertopHead(20, { d0: 4, tO: 0, count: 1, period: 0 }), 0, "tO=0");
  });
});

describe("energyHeadcutAdvance — dX = C·(q·H)^(1/3)·dt", () => {
  it("matches the hand value: C=1, q=8, H=8, dt=0.5 → cbrt(64)=4 → 2.0", () => {
    assertClose(energyHeadcutAdvance(1, 8, 8, 0.5), 2.0, 1e-12, "dX perfect-cube");
  });

  it("matches C=2, q=27, H=1, dt=1 → 2·cbrt(27)=2·3 = 6.0", () => {
    assertClose(energyHeadcutAdvance(2, 27, 1, 1), 6.0, 1e-12, "dX cbrt(27)");
  });

  it("scales as the cube root of q·H", () => {
    // Doubling the q·H product multiplies dX by 2^(1/3) = 1.25992105.
    const a = energyHeadcutAdvance(1, 10, 10, 1);
    const b = energyHeadcutAdvance(1, 20, 10, 1);
    assertClose(b / a, Math.cbrt(2), 1e-12, "cube-root scaling in q");
  });

  it("is linear in both C and dt", () => {
    const base = energyHeadcutAdvance(1, 8, 8, 1);
    assertClose(energyHeadcutAdvance(3, 8, 8, 1), 3 * base, 1e-12, "linear in C");
    assertClose(energyHeadcutAdvance(1, 8, 8, 2), 2 * base, 1e-12, "linear in dt");
  });

  it("clamps a non-positive drive or coefficient to zero", () => {
    assert.equal(energyHeadcutAdvance(1, -5, 3, 1), 0, "negative q·H");
    assert.equal(energyHeadcutAdvance(1, 5, -3, 1), 0, "negative H");
    assert.equal(energyHeadcutAdvance(-2, 8, 8, 1), 0, "negative C");
  });
});

describe("engine integration — wave→breach forcing (opt-in, regression-safe)", () => {
  // Rim-full, zero-inflow moraine pool (the Dig Tsho 1985 configuration): with no standing
  // head and no inflow the dam CANNOT breach on its own — only the wave supplies erosive head.
  const rimFull: StudioInputs = {
    ...DEFAULT_INPUTS,
    projectName: "wave-trigger regression",
    mode: "overtopping",
    damStructure: "moraine",
    baseElev: 0,
    crestElev: 18,
    initialWL: 18, // freeboard 0
    volumeM3: 5_000_000,
    surfaceAreaHa: 50,
    storageExponent: 1.8,
    inflowM3s: 0,
    spillwayQ: 0,
    crestWidth: 25,
    crestLength: 220,
    zUp: 1.8,
    zDown: 2.5,
    rhoD: 1900,
    phiDeg: 34,
    tauC: 4,
    erosionIndexI: 1.17,
    manningN: 0.035,
    sideErosionFactor: 1.3,
    initialNotchWidth: 5,
    Cw: 1.6,
    headcutEnabled: true,
    headcutInitDepth: 0.2,
    headcutAdvanceFactor: 8,
    headcutLaw: "energy",
    headcutEnergyCoeff: 1.0,
    waveOvertopDepth: 3.93,
    waveOvertopDuration: 41.7,
    waveOvertopCount: 3,
  };

  it("does NOT breach with the wave off, but DOES with it on (wave is the trigger)", () => {
    const off = runBreachSimulation({ ...rimFull, waveForcingEnabled: false });
    const on = runBreachSimulation({ ...rimFull, waveForcingEnabled: true });
    // Wave off: no standing head + no inflow ⇒ the invert never advances past its ~2 cm initial
    // notch, so discharge stays a negligible trickle (~0.02 m³/s, shown as "0.0" in the app) and
    // the breach does not initiate. Wave on: the transient crest head cuts the invert below still
    // water and the pool self-drains — a peak five orders of magnitude larger.
    assert.ok(off.Qpeak < 1, `expected no breach without the wave, got Qpeak=${off.Qpeak}`);
    assert.ok(off.finalDepth < 0.5, `expected the invert to stay at the initial notch, got ${off.finalDepth}`);
    assert.ok(on.Qpeak > 100 && Number.isFinite(on.Qpeak), `wave-on Qpeak=${on.Qpeak}`);
    assert.ok(on.Qpeak > 1000 * off.Qpeak, "wave-on peak not overwhelmingly larger than wave-off");
  });

  it("wave-forcing fields are INERT while the toggle is off (byte-identical peak/time)", () => {
    const noWave = runBreachSimulation({
      ...DEFAULT_INPUTS,
      mode: "overtopping",
      initialWL: DEFAULT_INPUTS.crestElev + 0.4, // a case that actually breaches
    });
    const withWaveFieldsButOff = runBreachSimulation({
      ...DEFAULT_INPUTS,
      mode: "overtopping",
      initialWL: DEFAULT_INPUTS.crestElev + 0.4,
      waveForcingEnabled: false,
      waveOvertopDepth: 5,
      waveOvertopDuration: 30,
      waveOvertopCount: 4,
      waveOvertopPeriod: 90,
    });
    assert.equal(withWaveFieldsButOff.Qpeak, noWave.Qpeak, "Qpeak changed under inert wave fields");
    assert.equal(withWaveFieldsButOff.tPeak, noWave.tPeak, "tPeak changed under inert wave fields");
  });

  it("wave forcing never activates outside overtopping mode (piping guard)", () => {
    const pipe = runBreachSimulation({ ...DEFAULT_INPUTS, mode: "piping" });
    const pipeWave = runBreachSimulation({
      ...DEFAULT_INPUTS,
      mode: "piping",
      waveForcingEnabled: true,
      waveOvertopDepth: 5,
      waveOvertopDuration: 30,
    });
    assert.equal(pipeWave.Qpeak, pipe.Qpeak, "wave leaked into a piping run");
  });

  it("emits engine warnings when wave forcing and the energy law are active", () => {
    const on = runBreachSimulation({ ...rimFull, waveForcingEnabled: true });
    assert.ok(
      on.warnings.some((w) => w.toLowerCase().includes("wave-overtopping forcing on")),
      "expected a wave-forcing engine warning",
    );
    assert.ok(
      on.warnings.some((w) => w.toLowerCase().includes("energy")),
      "expected an energy-headcut engine warning",
    );
  });
});

describe("engine integration — headcut law is selectable & defaults to hydrostatic", () => {
  const over: StudioInputs = {
    ...DEFAULT_INPUTS,
    mode: "overtopping",
    initialWL: DEFAULT_INPUTS.crestElev + 0.5,
  };

  it("the default (unspecified) law reproduces the explicit hydrostatic law exactly", () => {
    const dflt = runBreachSimulation(over);
    const hydro = runBreachSimulation({ ...over, headcutLaw: "hydrostatic" });
    assert.equal(dflt.Qpeak, hydro.Qpeak, "default != explicit hydrostatic Qpeak");
    assert.equal(dflt.tPeak, hydro.tPeak, "default != explicit hydrostatic tPeak");
  });

  it("the energy law runs and generally diverges from the hydrostatic law", () => {
    const hydro = runBreachSimulation({ ...over, headcutLaw: "hydrostatic" });
    const energy = runBreachSimulation({ ...over, headcutLaw: "energy", headcutEnergyCoeff: 1.0 });
    assert.ok(energy.Qpeak > 0 && Number.isFinite(energy.Qpeak), `energy Qpeak=${energy.Qpeak}`);
    assert.notEqual(energy.Qpeak, hydro.Qpeak, "laws gave identical Qpeak (energy law not wired?)");
  });
});


