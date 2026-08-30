import { create } from "zustand";
import { DEFAULT_INPUTS, type SimResult, type StudioInputs } from "@/lib/breach/types";
import {
  DEFAULT_IMPULSE_2D,
  DEFAULT_IMPULSE_3D,
  type Impulse2DInputs,
  type Impulse2DResult,
  type Impulse3DInputs,
  type Impulse3DResult,
} from "@/lib/impulse/types";

const STORAGE_KEY = "dam-breach-studio-v1";
const IMPULSE_KEY = "dam-breach-studio-impulse-v1";

function loadInputs(): StudioInputs {
  if (typeof window === "undefined") return DEFAULT_INPUTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_INPUTS;
    return { ...DEFAULT_INPUTS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_INPUTS;
  }
}

interface ImpulseSnapshot {
  dim: "2d" | "3d";
  p2: Impulse2DInputs;
  p3: Impulse3DInputs;
  r2: Impulse2DResult | null;
  r3: Impulse3DResult | null;
}

function loadImpulse(): ImpulseSnapshot {
  const base: ImpulseSnapshot = {
    dim: "2d",
    p2: { ...DEFAULT_IMPULSE_2D },
    p3: { ...DEFAULT_IMPULSE_3D },
    r2: null,
    r3: null,
  };
  if (typeof window === "undefined") return base;
  try {
    const raw = localStorage.getItem(IMPULSE_KEY);
    if (!raw) return base;
    return { ...base, ...JSON.parse(raw) };
  } catch {
    return base;
  }
}

interface StudioState {
  inputs: StudioInputs;
  result: SimResult | null;
  playIndex: number;
  running: boolean;
  impulse: ImpulseSnapshot;
  setInput: <K extends keyof StudioInputs>(key: K, value: StudioInputs[K]) => void;
  setInputs: (next: StudioInputs) => void;
  setResult: (result: SimResult | null) => void;
  setPlayIndex: (i: number) => void;
  setRunning: (v: boolean) => void;
  setImpulse: (patch: Partial<ImpulseSnapshot>) => void;
}

export const useStudio = create<StudioState>((set) => ({
  inputs: loadInputs(),
  result: null,
  playIndex: 0,
  running: false,
  impulse: loadImpulse(),
  setInput: (key, value) =>
    set((s) => {
      const inputs = { ...s.inputs, [key]: value };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(inputs));
      } catch {
        /* ignore */
      }
      return { inputs };
    }),
  setInputs: (inputs) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(inputs));
    } catch {
      /* ignore */
    }
    set({ inputs, result: null, playIndex: 0 });
  },
  setResult: (result) => set({ result, playIndex: result ? result.series.length - 1 : 0 }),
  setPlayIndex: (playIndex) => set({ playIndex }),
  setRunning: (running) => set({ running }),
  setImpulse: (patch) =>
    set((s) => {
      const impulse = { ...s.impulse, ...patch };
      try {
        localStorage.setItem(IMPULSE_KEY, JSON.stringify(impulse));
      } catch {
        /* ignore */
      }
      return { impulse };
    }),
}));
