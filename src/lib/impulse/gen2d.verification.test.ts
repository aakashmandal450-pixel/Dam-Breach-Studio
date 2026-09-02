/**
 * Tier 1 verification: computeImpulse2D() vs. the live VAW workbook.
 *
 * "Verification" here means: does our TypeScript reproduce what the VAW
 * spreadsheet's own formulas compute for the same inputs -- not whether the
 * VAW model itself matches reality (that's Tier 2 / case-study validation,
 * tracked separately under validation/).
 *
 * Reference values in validation/fixtures/2d_case_farfield.reference.json
 * were extracted by validation/tools/extract_vaw_fixture.py, which writes
 * real inputs into a scratch copy of
 * attachments/BFE_VAW_Impulse_Wave_Manual_Computational_Tool_v1-0.xlsm and
 * has LibreOffice recalculate the sheet's own Eq. 3.13-3.21 formulas. These
 * are NOT hand re-derived -- that was the failure mode behind the Phase 11B
 * bugs (PDF text extraction garbling the math).
 *
 * STATUS (Phase 12): all 19 assertions pass. Two bugs found by this harness
 * were fixed in gen2d.ts (and the matching mass bug in gen3d.ts):
 *
 * 1. `M` (relative slide mass) no longer applies an undocumented (1 - n/100)
 *    porosity reduction. The VAW sheet computes M18 = rhoS * Vsbulk /
 *    (1000 * b * h^2) directly, with no porosity term -- confirmed by
 *    recalculating the live sheet and comparing cell-for-cell.
 *
 * 2. `Hx`/`Tx` (far-field wave height/period at distance x) now recompute
 *    directly from P and X = x/h via Eq. 3.19/3.20, matching the VAW sheet,
 *    instead of decaying the near-field peak by (xM/x)^(4/15) -- the two
 *    forms are not algebraically equivalent (different exponents on P).
 *
 * If this file goes red again after a future change, treat it the same way:
 * don't "fix" the fixture to match the code -- the fixture is ground truth
 * pulled from the reference tool, so a mismatch means the code regressed.
 */
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { computeImpulse2D } from "./gen2d.ts";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURE_PATH = join(
  __dirname,
  "../../../validation/fixtures/2d_case_farfield.reference.json",
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
    x: number;
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

describe("computeImpulse2D vs. VAW workbook (Generation | Propagation 2D)", () => {
  const fixture = loadFixture();
  const result = computeImpulse2D({
    fallHeight: fixture.inputs.h, // unused by computeImpulse2D directly
    Vs: fixture.inputs.Vs,
    autoVelocity: false,
    slideVolume: fixture.inputs.slideVolume,
    s: fixture.inputs.s,
    b: fixture.inputs.b,
    rhoS: fixture.inputs.rhoS,
    nPercent: fixture.inputs.nPercent,
    alphaDeg: fixture.inputs.alphaDeg,
    h: fixture.inputs.h,
    x: fixture.inputs.x,
  });
  const ref = fixture.reference;
  const TOL = 1e-6; // relative tolerance -- should match to floating point precision

  it("F (slide Froude number) matches", () => {
    assertClose(result.F, ref.F, TOL, "F");
  });

  it("S (relative slide thickness) matches", () => {
    assertClose(result.S, ref.S, TOL, "S");
  });

  it("D (relative slide density) matches", () => {
    assertClose(result.D, ref.D, TOL, "D");
  });

  it("Vrel (relative slide volume) matches", () => {
    assertClose(result.Vrel, ref.Vrel, TOL, "Vrel");
  });

  it("B (relative slide width) matches", () => {
    assertClose(result.B, ref.B, TOL, "B");
  });

  it("X (relative streamwise distance) matches", () => {
    assertClose(result.X, ref.X, TOL, "X");
  });

  it("M (relative slide mass) matches", () => {
    assertClose(result.M, ref.M, TOL, "M");
  });

  it("P (impulse product parameter) matches", () => {
    assertClose(result.P, ref.P, TOL, "P");
  });

  it("HM (max wave height) matches", () => {
    assertClose(result.HM, ref.HM, TOL, "HM");
  });

  it("aM (max wave amplitude) matches", () => {
    assertClose(result.aM, ref.aM, TOL, "aM");
  });

  it("xM (distance of aM) matches", () => {
    assertClose(result.xM, ref.xM, TOL, "xM");
  });

  it("TM (wave period at xM) matches", () => {
    assertClose(result.TM, ref.TM, TOL, "TM");
  });

  it("cXM (wave celerity at xM) matches", () => {
    assertClose(result.cXM, ref.cXM, TOL, "cXM");
  });

  it("LM (wave length at xM) matches", () => {
    assertClose(result.LM, ref.LM, TOL, "LM");
  });

  it("Hx (wave height at x) matches", () => {
    assertClose(result.Hx, ref.Hx, TOL, "Hx");
  });

  it("ax (wave amplitude at x) matches", () => {
    assertClose(result.ax, ref.ax, TOL, "ax");
  });

  it("Tx (wave period at x) matches", () => {
    assertClose(result.Tx, ref.Tx, TOL, "Tx");
  });

  it("cx (wave celerity at x) matches", () => {
    assertClose(result.cx, ref.cx, TOL, "cx");
  });

  it("Lx (wave length at x) matches", () => {
    assertClose(result.Lx, ref.Lx, TOL, "Lx");
  });
});
