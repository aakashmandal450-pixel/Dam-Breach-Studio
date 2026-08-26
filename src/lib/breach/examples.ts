import { DEFAULT_INPUTS, type StudioInputs } from "./types";

export interface ExampleCase {
  id: string;
  title: string;
  blurb: string;
  inputs: StudioInputs;
}

export const EXAMPLES: ExampleCase[] = [
  {
    id: "overtop-moderate",
    title: "Overtopping — moderately erodible fill",
    blurb: "12 m homogeneous earthfill, pool just above the crest. I = 3.2 (CL/SM range).",
    inputs: { ...DEFAULT_INPUTS },
  },
  {
    id: "piping-moderate",
    title: "Piping — concentrated leak through the core",
    blurb: "Same dam, pool 1 m below crest. Pipe starts at 8 cm radius and enlarges until roof collapse.",
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
