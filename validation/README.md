# Validation

This folder holds the **Tier 1 (verification)** harness: proof that the
TypeScript engine reproduces what the reference spreadsheets compute for
matched inputs. It is deliberately separate from **Tier 2 (validation)** --
comparison against real historical dam/GLOF events -- which will live under
`validation/cases/` once a case library exists. Conflating the two is how
"validation" efforts usually stall: verification is cheap and mechanical,
validation requires hunting down and vetting real-world data.

## Why fixtures are extracted, not hand-derived

The reference spreadsheets (VAW workbook, Break-1/2/3/5, Flood-1) ship with
their input cells blank, so there's no worked example baked in to read
directly. `validation/tools/extract_vaw_fixture.py` writes real inputs into
a scratch copy, forces LibreOffice to recalculate every formula headlessly,
and reads back what the sheet's own live formulas produce. That's the same
class of mistake that caused the Phase 11B bugs (PDF-extracted equations
garbling coefficients) -- re-typing formulas by hand from a PDF or a memory
of the paper is exactly what this harness exists to avoid.

## Layout

```
validation/
  tools/
    extract_vaw_fixture.py   # regenerate a fixture from the live workbook
  fixtures/
    *.reference.json          # clean {inputs, reference} pairs consumed by tests
    raw/*.json                 # raw cell dump from the extractor (provenance)
```

Corresponding test files live next to the code they check, named
`*.verification.test.ts` (e.g. `src/lib/impulse/gen2d.verification.test.ts`),
and run separately from the main suite:

```
npm run test:verify
```

They are **not** part of `npm test`. Some of them currently fail on purpose
-- see "Current status" below -- and folding known-red tests into the main
suite either hides them (if someone routes around failures) or breaks the
green-CI convention the rest of the repo relies on. `test:verify` is the
place to check when you want the honest answer to "does the code match the
reference tool right now."

## Adding a new fixture

```
python3 validation/tools/extract_vaw_fixture.py --sheet 2d \
  --out validation/fixtures/2d_case_<name>.raw.json \
  Vs=<m/s> Vsbulk=<m3> s=<m> b=<m> rhoS=<kg/m3> n=<%> alpha=<deg> h=<m> x=<m>
```

Then hand-copy the relevant `raw_cells` values into a `*.reference.json`
in the clean `{inputs, reference}` shape the test files expect (see
`2d_case_farfield.reference.json` for the format), and write a
`*.verification.test.ts` that loads it and asserts against
`computeImpulse2D`/`computeImpulse3D`/etc.

Do the same pattern for `Break-1/2/3/5-metric.xls`, `Flood-1-metric.xls`,
and `SurfArea-metric.xls` once the breach engine and lake-volume modules
get their own verification passes -- the extractor is VAW-specific right
now (cell layout is hardcoded) but the recalculate-then-read-back approach
generalizes directly.

## Current status

| Module | Fixture | Status |
|---|---|---|
| `impulse/gen2d.ts` | `2d_case_farfield.reference.json` (x=300m, beyond xM) | **19/19 pass** (Phase 12 fix). |
| `impulse/gen3d.ts` | `3d_case_farfield.reference.json` (r=300m, γ=20°, beyond r0(γ)) | **6/6 pass** (Phase 12 full rewrite — see below). |
| `breach/engine.ts` | -- | Not yet fixtured. No direct spreadsheet analog (mechanistic engine vs. Fread/BREACH-style tools) -- needs case-study (Tier 2) validation more than cell-matching. |
| `lake/volume.ts` | -- | Not yet fixtured. Pure regression formulas -- verification here means checking coefficients against the source papers directly, not a spreadsheet. Lower priority; low bug surface. |

### gen3d.ts: full rewrite (Phase 12)

The previous 3D module used a simplified single-wave model (`cos²(γ)`
directional falloff, one amplitude/height pair, `r^-1` mean decay) already
flagged in its docstring as provisional/unverified. Pulling the live 3D
sheet's formulas revealed it's structurally different from that
simplification: VAW tracks **three separate wave components** (leading
crest `ac1`, trough `at1`, second crest `ac2`), each with its own
SECH-based directional decay, and a near-field boundary that's itself an
ellipse combining the along-axis (`r0,0°`) and cross-axis (`r0,90°`)
radii -- there's no single "peak wave" the way the 2D model has.

`gen3d.ts` was rewritten to match this exactly (Eq. 3.22-3.35), confirmed
against `3d_case_farfield.reference.json` including a nonzero γ (20°) to
exercise the SECH directional term, not just the on-axis case where several
formulas degenerate to simpler forms. The old, unsourced limitation ranges
(Table 3-3 bounds) were also replaced with the real ones from the sheet's
`L` column -- they didn't match either.

`Impulse3DResult` changed shape as part of this (now exposes `ac1`/`at1`/`ac2`
individually, `insideNearField`, `r0_0`/`r0_90`/`r0Gamma`, etc., alongside
`aM`/`HM`/`TM`/`rM` kept as convenience aliases for run-up/breach chaining
so the UI and `computeRunup()` call sites didn't need to change). The
`Impulse3DSchematic` component was updated to show the three real
components instead of the old (now-removed) `ar`/`Hr` duplicate fields.

### Bugs found and fixed (gen2d.ts, and the same pattern in gen3d.ts)

1. **`M` (relative slide mass) had an undocumented porosity correction.**
   The VAW sheet computes `M = rhoS * Vsbulk / (1000 * b * h^2)` directly.
   The code was additionally multiplying by `(1 - n/100)` before forming the
   mass. Confirmed numerically: the app's `M` was low by exactly a factor of
   `(1 - n/100)` for every case checked. This single term propagated into
   `P` and every `P`-dependent output (`HM`, `aM`, `xM`, `TM`, `cXM`, `LM`)
   -- roughly an 8-9% underestimate of near-field wave height/amplitude at
   n=35%, growing with porosity. Same subtraction existed in `gen3d.ts`.
   **Fixed** in both files by using the bulk slide mass directly.

2. **Far-field decay (`Hx`, `Tx`, and everything downstream) used a
   different functional form than the VAW sheet's Eq. 3.19/3.20.** The code
   decayed the near-field peak by `(xM/x)^(4/15)`. The sheet instead
   recomputes directly from `P` and `X = x/h`. These were not algebraically
   equivalent -- the exponent on `P` differs (14/15 in the code's implied
   form vs. 4/5 in the sheet). **Fixed** in `gen2d.ts` by recomputing `Hx`,
   `ax`, and `Tx` directly from `P` and `X` per the sheet's formula.
   `gen3d.ts`'s far-field decay was left untouched -- it already had no
   direct VAW analog and is disclosed as a provisional `r^-1` mean rather
   than a formula claiming spreadsheet-fidelity.

`src/lib/impulse/gen2d.verification.test.ts` encodes both fixes as
assertions against the live-workbook fixture (`npm run test:verify`, 19/19
passing). If a future change to `gen2d.ts` makes this file fail again,
treat that as a real regression -- the fixture is ground truth from the
reference tool, not something to edit to match new code.
