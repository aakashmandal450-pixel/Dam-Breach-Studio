
import type { DamStructure } from "./types";

/** Screening defaults for headcut initiation and advance by dam structure. */
export function headcutDefaultsForStructure(s: DamStructure | undefined): {
  headcutEnabled: boolean;
  headcutInitDepth: number;
  headcutAdvanceFactor: number;
} {
  switch (s) {
    case "moraine":
    case "ice_cored_moraine":
      // Debris often erodes more as surface lowering; milder discrete headcut
      return { headcutEnabled: true, headcutInitDepth: 0.03, headcutAdvanceFactor: 4 };
    case "zoned":
      // Clay core / resistant shell: clearer headcut, slower advance
      return { headcutEnabled: true, headcutInitDepth: 0.05, headcutAdvanceFactor: 8 };
    case "homogeneous":
    default:
      return { headcutEnabled: true, headcutInitDepth: 0.04, headcutAdvanceFactor: 6 };
  }
}
