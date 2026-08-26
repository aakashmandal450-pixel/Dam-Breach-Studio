import { DEFAULT_INPUTS, type StudioInputs } from "./types";

export interface ExampleCase {
  id: string;
  title: string;
  blurb: string;
  /** Longer explanation for the Theory page. */
  theory: string;
  inputs: StudioInputs;
}

export const EXAMPLES: ExampleCase[] = [
  {
    id: "overtop-moderate",
    title: "Overtopping — moderately erodible fill",
    blurb: "12 m homogeneous earthfill, pool just above the crest. I = 3.2 (CL/SM range).",
    theory:
      "Baseline teaching case. A modest overtopping head starts a notch; the headcut module migrates through the crest width before full deepening. I = 3.2 sits in the moderately erodible band (many CL/SM fills). Use this run to learn the stage sequence filling → headcut → open → empty and to read peak Q, time to peak, and final breach geometry.",
    inputs: { ...DEFAULT_INPUTS },
  },
  {
    id: "piping-moderate",
    title: "Piping — concentrated leak through the core",
    blurb: "Same dam, pool 1 m below crest. Pipe starts at 8 cm radius and enlarges until roof collapse.",
    theory:
      "Internal erosion path. Flow is orifice-like until the pipe diameter meets the collapse criterion (2R ≥ κ × cover). After roof collapse the model switches to an open trapezoidal weir. Compare time-to-collapse with the simplified Bonelli Δt screening formula (constant head): the full simulation uses a falling reservoir, so times usually differ. Key outputs: roof-collapse time, then peak Q on the open-breach limb.",
    inputs: {
      ...DEFAULT_INPUTS,
      projectName: "Homogeneous earthfill — piping",
      mode: "piping",
      initialWL: 11,
      volumeM3: 150000,
      inflowM3s: 0.4,
      pipeInvert: 4,
      initialPipeRadius: 0.08,
      erosionIndexI: 3.0,
    },
  },
  {
    id: "overtop-resistant",
    title: "Overtopping — erosion-resistant clay",
    blurb: "Higher plasticity core (I = 4.6). Breach grows slowly; useful contrast on soil control.",
    theory:
      "Soil-control contrast. Raising I by about 1.4 units (vs the baseline) reduces the erosion coefficient Ce = 10^(−I) by more than an order of magnitude. Peak discharge is lower and later; headcut advance is slow. Demonstrates why laboratory HET/JET values dominate uncertainty — geometry alone does not set the hydrograph.",
    inputs: {
      ...DEFAULT_INPUTS,
      projectName: "Resistant clay — overtopping",
      erosionIndexI: 4.6,
      tauC: 25,
      phiDeg: 28,
      tMaxHours: 12,
      initialWL: 12.2,
    },
  },
  {
    id: "overtop-rapid",
    title: "Overtopping — rapidly erodible silt",
    blurb: "Low I = 2.2. Expect a short, sharp hydrograph — typical of SM/ML fills.",
    theory:
      "Rapidly erodible end-member (SM/ML-like). Low I and low τc produce a short, peaked hydrograph. Useful as a bounding case for emergency planning discussions, but not a substitute for site-specific testing. Watch for numerical sensitivity: very low I can make enlargement extremely fast relative to the chosen time step.",
    inputs: {
      ...DEFAULT_INPUTS,
      projectName: "Rapid silt — overtopping",
      erosionIndexI: 2.2,
      tauC: 2,
      phiDeg: 34,
      tMaxHours: 3,
      initialNotchWidth: 0.8,
    },
  },
];
