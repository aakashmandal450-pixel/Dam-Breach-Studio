/**
 * Tier 2 case-study runner.
 *
 * Loads a case JSON (see teton-1976.json / dig-tsho-1985.json for shape),
 * merges its inputOverrides onto DEFAULT_INPUTS, runs the real
 * runBreachSimulation() engine, and reports simulated vs. observed
 * peak discharge and breach-formation time as a plain percentage error.
 *
 * This deliberately does NOT hardcode a pass/fail tolerance -- see
 * validation/cases/README.md for why. It also prints which inputs came
 * from a source vs. a typical-value placeholder, so the error number is
 * never read without that context sitting right next to it.
 *
 * Usage:
 *   npm run validate:case -- validation/cases/teton-1976.json
 *
 * (Runs via jiti, not plain node -- engine.ts/types.ts use extensionless
 * imports that match Vite's bundler resolution but not Node's native ESM
 * loader. jiti resolves them the same way the app itself does.)
 */
import { readFileSync } from "node:fs";
import { DEFAULT_INPUTS, type StudioInputs } from "../../src/lib/breach/types.ts";
import { runBreachSimulation } from "../../src/lib/breach/engine.ts";

interface ObservedValue {
  value: number | null;
  range?: [number, number];
  note?: string;
  source?: string | null;
}

interface CaseFile {
  id: string;
  name: string;
  eventDate: string;
  sources: { citation: string; url: string }[];
  inputOverrides: Partial<StudioInputs>;
  sourced: Record<string, string>;
  unsourcedFields: string[];
  unsourcedFieldsNote: string;
  observed: {
    peakDischargeM3s: ObservedValue;
    breachFormationHours: ObservedValue;
  };
}

function pctError(simulated: number, observed: number): string {
  const err = ((simulated - observed) / observed) * 100;
  const sign = err >= 0 ? "+" : "";
  return `${sign}${err.toFixed(1)}%`;
}

function main() {
  const path = process.argv[2];
  if (!path) {
    console.error("Usage: run_case.ts <case.json>");
    process.exit(1);
  }

  const caseFile: CaseFile = JSON.parse(readFileSync(path, "utf-8"));
  const inputs: StudioInputs = { ...DEFAULT_INPUTS, ...caseFile.inputOverrides };

  const result = runBreachSimulation(inputs);

  console.log(`\n=== ${caseFile.name} (${caseFile.eventDate}) ===\n`);

  console.log("Sourced inputs:");
  for (const [key, note] of Object.entries(caseFile.sourced)) {
    console.log(`  ${key} = ${String((inputs as Record<string, unknown>)[key])}  (${note})`);
  }

  console.log(`\nUnsourced/placeholder inputs (${caseFile.unsourcedFields.length}):`);
  console.log(`  ${caseFile.unsourcedFields.join(", ")}`);
  console.log(`  Note: ${caseFile.unsourcedFieldsNote}\n`);

  console.log("--- Results ---");
  console.log(`Simulated Qpeak:        ${result.Qpeak.toFixed(1)} m3/s`);
  const obsQ = caseFile.observed.peakDischargeM3s;
  if (obsQ.value != null) {
    console.log(`Observed Qpeak:         ${obsQ.value} m3/s${obsQ.range ? ` (range ${obsQ.range[0]}-${obsQ.range[1]})` : ""}`);
    console.log(`Error:                  ${pctError(result.Qpeak, obsQ.value)}`);
  } else {
    console.log("Observed Qpeak:         not available for this case");
  }
  if (obsQ.note) console.log(`  note: ${obsQ.note}`);

  console.log();
  const tPeakHours = result.tPeak / 3600;
  console.log(`Simulated t_peak:       ${tPeakHours.toFixed(2)} h`);
  const obsT = caseFile.observed.breachFormationHours;
  if (obsT.value != null) {
    console.log(`Observed breach time:   ${obsT.value} h`);
    console.log(`Error:                  ${pctError(tPeakHours, obsT.value)}`);
  } else {
    console.log("Observed breach time:   not available for this case");
  }
  if (obsT.note) console.log(`  note: ${obsT.note}`);

  if (result.warnings.length > 0) {
    console.log(`\nEngine warnings: ${result.warnings.join("; ")}`);
  }

  console.log(`\nSources:`);
  for (const s of caseFile.sources) console.log(`  - ${s.citation}\n    ${s.url}`);
  console.log();
}

main();
