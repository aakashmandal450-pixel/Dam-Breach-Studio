/**
 * Tier 1 verification for the erosion closures added in improvement #1
 * (dual erosion law + re-anchored kd).
 *
 * "Verification" = does the TypeScript reproduce the closed-form physics for the
 * same inputs. The reference numbers below are hand-derived from the governing
 * equations (Meyer-Peter–Müller + Smart gradation → Exner; Hanson & Simon JET
 * regression) and re-derived independently in-test, so a mismatch means the code
 * drifted from the math — not that the fixture is stale.
 *
 * Run: node --experimental-strip-types --test src/lib/breach/erosion.verification.test.ts
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  kdForMode,
  mpmSmartErosionRate,
  shieldsStress,
  runBreachSimulation,
  type TransportCapacityOpts,
} from "./engine.ts";
import { DEFAULT_INPUTS, type StudioInputs } from "./types.ts";

const G = 9.81;
const RHO = 1000;

function assertClose(actual: number, expected: number, relTol: number, label: string): void {
  const diff = Math.abs(actual - expected);
  const tol = Math.max(Math.abs(expected) * relTol, 1e-12);
  assert.ok(
    diff <= tol,
    `${label}: got ${actual}, expected ${expected} (diff ${diff}, tol ${tol})`,
  );
}

/** Independent re-implementation of the MPM/Smart/Exner rate for cross-checking. */
function refMpmSmart(tau: number, o: TransportCapacityOpts): number {
  const s = o.grainDensity / RHO;
  const D = o.grainD50_m;
  const theta = tau / ((s - 1) * RHO * G * D);
  const excess = theta - o.criticalShields;
  if (excess <= 0) return 0;
  const phi = o.mpmCoefficient * Math.pow(o.grainD90D30Ratio, 0.2) * Math.pow(excess, 1.5);
  const qs = phi * Math.sqrt((s - 1) * G * D * D * D);
  return qs / ((1 - o.porosity) * o.reachLength);
}

describe("Shields stress θ = τ / ((s−1) ρ g D50)", () => {
  it("matches hand calculation for τ=200, ρs=2650, D50=0.03", () => {
    // (2.65−1)·1000·9.81·0.03 = 485.595 ; 200/485.595 = 0.4118679…
    assertClose(shieldsStress(200, 2650, 0.03), 0.4118679, 1e-5, "θ");
  });
  it("scales inversely with D50", () => {
    const a = shieldsStress(200, 2650, 0.03);
    const b = shieldsStress(200, 2650, 0.06);
    assertClose(b, a / 2, 1e-9, "θ(2·D50)");
  });
});

describe("mpmSmartErosionRate — MPM + Smart gradation → Exner", () => {
  const o: TransportCapacityOpts = {
    grainDensity: 2650,
    grainD50_m: 0.03,
    grainD90D30Ratio: 8,
    criticalShields: 0.047,
    mpmCoefficient: 8,
    porosity: 0.35,
    reachLength: 50,
  };

  it("matches the hand-derived rate at τ = 200 Pa (≈ 1.719 mm/s)", () => {
    // θ=0.411868 → excess=0.364868 → excess^1.5=0.220378
    // Φ = 8·(8^0.2=1.515717)·0.220378 = 2.67246
    // qs = Φ·√(1.65·9.81·0.03³=4.3704e-4 → 0.0209053) = 0.055869 m²/s
    // ε = 0.055869/(0.65·50=32.5) = 0.00171906 m/s
    assertClose(mpmSmartErosionRate(200, o), 0.00171906, 2e-3, "ε(200)");
  });

  it("agrees with an independent re-implementation across a τ sweep", () => {
    for (const tau of [10, 25, 60, 120, 200, 400, 800]) {
      assertClose(mpmSmartErosionRate(tau, o), refMpmSmart(tau, o), 1e-9, `ε(${tau})`);
    }
  });

  it("returns 0 below the Shields threshold", () => {
    // θc=0.047 → τ_threshold = 0.047·(s−1)·ρ·g·D50 = 0.047·485.595 ≈ 22.8 Pa
    assert.equal(mpmSmartErosionRate(20, o), 0, "below-threshold rate");
    assert.ok(mpmSmartErosionRate(25, o) > 0, "just-above-threshold rate");
  });

  it("is monotonic increasing in τ", () => {
    let prev = -1;
    for (const tau of [30, 50, 100, 200, 400]) {
      const e = mpmSmartErosionRate(tau, o);
      assert.ok(e > prev, `monotonic at τ=${tau} (got ${e}, prev ${prev})`);
      prev = e;
    }
  });

  it("well above threshold approaches the τ^1.5-limited (D50-independent) regime", () => {
    // For θ ≫ θc, qs ∝ θ^1.5·D50^1.5 ∝ τ^1.5, independent of D50.
    const big = 5000;
    const coarse = mpmSmartErosionRate(big, o);
    const fine = mpmSmartErosionRate(big, { ...o, grainD50_m: 0.06 });
    assertClose(coarse, fine, 0.02, "high-shear D50 independence");
  });
});

describe("kdForMode — erodibility provenance", () => {
  it("index: kd = 10^(−I)/ρd (legacy, unchanged)", () => {
    assertClose(kdForMode("index", 3.2, 8, 1800, 0.5), Math.pow(10, -3.2) / 1800, 1e-12, "kd_index");
  });
  it("hanson: kd = 2e-7·τc^(−0.5) [SI]", () => {
    // 2e-7·8^(−0.5) = 2e-7·0.3535534 = 7.071068e-8
    assertClose(kdForMode("hanson", 3.2, 8, 1800, 0.5), 7.071068e-8, 1e-5, "kd_hanson");
  });
  it("direct: cm³/(N·s) → SI ×1e-6", () => {
    assertClose(kdForMode("direct", 3.2, 8, 1800, 0.5), 5e-7, 1e-12, "kd_direct");
  });
});

describe("engine integration — defaults preserved, closure wired", () => {
  it("default inputs (excess_shear + index) breach with a finite peak", () => {
    const r = runBreachSimulation(DEFAULT_INPUTS);
    assert.ok(Number.isFinite(r.Qpeak) && r.Qpeak > 0, `default Qpeak = ${r.Qpeak}`);
  });

  it("excess_shear results are INERT to transport-capacity grain params", () => {
    // Grain params must not touch the legacy path — regression guard.
    const base = runBreachSimulation(DEFAULT_INPUTS);
    const perturbed = runBreachSimulation({
      ...DEFAULT_INPUTS,
      grainD50_m: 0.2,
      grainD90D30Ratio: 25,
      grainDensity: 2900,
      criticalShields: 0.03,
      mpmCoefficient: 4,
      porosity: 0.5,
    });
    assert.equal(perturbed.Qpeak, base.Qpeak, "Qpeak changed under inert grain params");
    assert.equal(perturbed.tPeak, base.tPeak, "tPeak changed under inert grain params");
  });

  it("transport_capacity is wired and differs from excess_shear on a granular overtopping dam", () => {
    // A cohesionless overtopping embankment that actually breaches under both closures.
    const granular: StudioInputs = {
      ...DEFAULT_INPUTS,
      projectName: "granular overtopping test",
      mode: "overtopping",
      damStructure: "homogeneous",
      headcutEnabled: false, // isolate the open-breach closure from the headcut gate
      crestElev: 20,
      baseElev: 0,
      initialWL: 20.3,
      volumeM3: 4_000_000,
      inflowM3s: 30,
      erosionIndexI: 2.2,
      tauC: 3,
      manningN: 0.03,
    };
    const es = runBreachSimulation({ ...granular, erosionModel: "excess_shear" });
    const tc = runBreachSimulation({ ...granular, erosionModel: "transport_capacity", grainD50_m: 0.02 });
    assert.ok(es.Qpeak > 0, `excess_shear Qpeak = ${es.Qpeak}`);
    assert.ok(tc.Qpeak > 0, `transport_capacity Qpeak = ${tc.Qpeak}`);
    assert.notEqual(tc.Qpeak, es.Qpeak, "closures produced identical Qpeak (branch not active?)");
    assert.ok(
      tc.warnings.some((w) => w.includes("transport-capacity")),
      "expected a transport-capacity engine warning",
    );
  });

  it("hanson kd mode runs and pins n=1 (piping case)", () => {
    const r = runBreachSimulation({ ...DEFAULT_INPUTS, mode: "piping", kdMode: "hanson" });
    assert.ok(Number.isFinite(r.Qpeak) && r.Qpeak > 0, `hanson Qpeak = ${r.Qpeak}`);
    assert.ok(
      r.warnings.some((w) => w.includes("Hanson")),
      "expected a Hanson kd engine warning",
    );
  });
});
