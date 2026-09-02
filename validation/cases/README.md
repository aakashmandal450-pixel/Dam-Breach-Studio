# Tier 2 — Case-study validation

Where Tier 1 (`validation/README.md`, one level up) checks the code against
reference *spreadsheets*, Tier 2 checks it against real, documented failures.
This is where "does the physics work" gets tested against "did anyone
actually observe this happening."

## Honesty rule: every input is tagged sourced or assumed

Real events almost never come with a full, clean input set — you get a peak
discharge and a dam height from a USGS report, not a full geotechnical
erodibility survey. Each case file separates:

- **`inputOverrides`** — engine inputs pulled from `DEFAULT_INPUTS` and
  overridden with case-specific values
- **`sourced`** — which of those override keys are backed by a citation in
  `sources`, with the citation attached
- **`unsourcedFields`** — which override keys are engineering-judgment
  placeholders (typical values for the dam type), *not* from the event
  itself. These exist so the simulation can run at all, but any comparison
  should weight them accordingly — a case with erosion parameters guessed
  from "typical zoned earthfill" values isn't testing whether the model
  predicts *that dam's* breach, only whether it produces something in a
  plausible range given plausible inputs.

This matters because it's the difference between "the model got peak
discharge within 8% of Teton" (meaningful) and silently feeding it made-up
erodibility numbers that happen to produce a good-looking number (worthless,
and the kind of thing that undermines a published validation document the
moment someone checks the sourcing).

## Error metrics

`run_case.ts` computes, for each case:
- `%error(Qpeak)` = (simulated − observed) / observed, for peak discharge
- `%error(t_formation)` = same, for breach formation / time-to-peak

No pass/fail threshold is hardcoded — dam-breach peak-discharge prediction
is widely accepted in the literature to carry order-of-magnitude uncertainty
even from calibrated models, so a single tolerance band would be more
misleading than the raw percentage.

## Running the cases

```
npm run validate:case -- validation/cases/teton-1976.json
npm run validate:case -- validation/cases/dig-tsho-1985.json
```

(Runs via `jiti`, added as a devDependency, since `engine.ts`/`types.ts` use
extensionless imports that Vite's bundler resolves but Node's native ESM
loader won't. `jiti` resolves them the same way the app itself does.)

## Case status

| Case | Type | Completeness |
|---|---|---|
| `teton-1976.json` | Engineered earthfill, piping | Geometry, reservoir volume, and observed peak discharge/timing are sourced. Erodibility/pipe parameters (rhoD, phiDeg, tauC, erosionIndexI, CdOrifice, pipe geometry) are typical-value placeholders — the actual Bureau of Reclamation forensic report would have real values and should replace these. |
| `dig-tsho-1985.json` | Moraine/GLOF, wave-triggered overtopping | Moraine height, lake volume, and observed peak discharge are sourced (with a genuine range across studies — sources disagree by ~15%, reported as-is rather than picking one). Geometry (crest width/length, side slopes) and all erodibility parameters are unsourced placeholders. Treat this one as a seed case, not a validated result, until better-sourced geometry is found. |

Add a new case by copying the JSON shape in either file, running it through
`run_case.ts`, and adding a row to the table above.
