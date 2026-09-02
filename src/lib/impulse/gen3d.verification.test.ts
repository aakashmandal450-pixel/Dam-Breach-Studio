/**
 * Tier 1 verification: computeImpulse3D() vs. the live VAW workbook.
 *
 * Same methodology as gen2d.verification.test.ts (see that file's header),
 * against the "Generation | Propagation (3D)" sheet this time. Fixture uses
 * a nonzero γ (20°) specifically to exercise the SECH-based directional
 * decay term, not just the on-axis γ=0 case where several formulas
 * degenerate to simpler forms.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { computeImpulse3D } from "./gen3d.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURE_PATH = join(
  __dirname,
  "../../../validation/fixtures/3d_case_farfield.reference.json",
);

interface Fixture {
  inputs: {
    Vs: number;
    slideVolume: number;
    s: number;
    b: number;
    rhoS: number;
    nPercent: number;
    alphaDeg: number;
    h: number;
    r: number;
    gammaDeg: number;
  };
  reference: Record<string, number>;
}

function loadFixture(): Fixture {
  return JSON.parse(readFileSync(FIXTURE_PATH, "utf-8"));
}

function assertClose(actual: number, expected: number, relTol: number, label: string): void {
  const diff = Math.abs(actual - expected);
  const tol = Math.max(Math.abs(expected) * relTol, 1e-9);
  assert.ok(
    diff <= tol,
    `${label}: got ${actual}, expected ${expected} (diff ${diff}, tol ${tol.toFixed(6)})`,
  );
}

describe("computeImpulse3D vs. VAW workbook (Generation | Propagation 3D)", () => {
  const fixture = loadFixture();
  const result = computeImpulse3D({
    fallHeight: fixture.inputs.h,
    Vs: fixture.inputs.Vs,
    autoVelocity: false,
    slideVolume: fixture.inputs.slideVolume,
    s: fixture.inputs.s,
    b: fixture.inputs.b,
    rhoS: fixture.inputs.rhoS,
    nPercent: fixture.inputs.nPercent,
    alphaDeg: fixture.inputs.alphaDeg,
    h: fixture.inputs.h,
    r: fixture.inputs.r,
    gammaDeg: fixture.inputs.gammaDeg,
  });
  const ref = fixture.reference;
  const TOL = 1e-6;

  it("F, S, M, D, rhoGRatio, Vrel, B, Rrel, P match", () => {
    assertClose(result.F, ref.F, TOL, "F");
    assertClose(result.S, ref.S, TOL, "S");
    assertClose(result.M, ref.M, TOL, "M");
    assertClose(result.D, ref.D, TOL, "D");
    assertClose(result.rhoGRatio, ref.rhoGRatio, TOL, "rhoGRatio");
    assertClose(result.Vrel, ref.Vrel, TOL, "Vrel");
    assertClose(result.B, ref.B, TOL, "B");
    assertClose(result.Rrel, ref.Rrel, TOL, "Rrel");
    assertClose(result.P, ref.P, TOL, "P");
  });

  it("r0_0, r0_90, r0Gamma, rStar match", () => {
    assertClose(result.r0_0, ref.r0_0, TOL, "r0_0");
    assertClose(result.r0_90, ref.r0_90, TOL, "r0_90");
    assertClose(result.r0Gamma, ref.r0Gamma, TOL, "r0Gamma");
    assertClose(result.rStar, ref.rStar, TOL, "rStar");
  });

  it("a0c1, a0t1, a0c2 (near-field boundary amplitudes) match", () => {
    assertClose(result.a0c1, ref.a0c1, TOL, "a0c1");
    assertClose(result.a0t1, ref.a0t1, TOL, "a0t1");
    assertClose(result.a0c2, ref.a0c2, TOL, "a0c2");
  });

  it("case is correctly identified as beyond the near field", () => {
    assert.equal(result.insideNearField, false);
  });

  it("ac1, at1, ac2 (far-field amplitudes) match", () => {
    assert.ok(result.ac1 != null && result.at1 != null && result.ac2 != null);
    assertClose(result.ac1!, ref.ac1, TOL, "ac1");
    assertClose(result.at1!, ref.at1, TOL, "at1");
    assertClose(result.ac2!, ref.ac2, TOL, "ac2");
  });

  it("cc1, cc2, T1, L1 match", () => {
    assert.ok(result.cc1 != null && result.cc2 != null && result.T1 != null && result.L1 != null);
    assertClose(result.cc1!, ref.cc1, TOL, "cc1");
    assertClose(result.cc2!, ref.cc2, TOL, "cc2");
    assertClose(result.T1!, ref.T1, TOL, "T1");
    assertClose(result.L1!, ref.L1, TOL, "L1");
  });
});
