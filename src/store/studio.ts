import { create } from "zustand";
import { DEFAULT_INPUTS, type SimResult, type StudioInputs } from "@/lib/breach/types";

const STORAGE_KEY = "dam-breach-studio-v1";

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

interface StudioState {
  inputs: StudioInputs;
  result: SimResult | null;
  playIndex: number;
  running: boolean;
  setInput: <K extends keyof StudioInputs>(key: K, value: StudioInputs[K]) => void;
  setInputs: (next: StudioInputs) => void;
  setResult: (result: SimResult | null) => void;
  setPlayIndex: (i: number) => void;
  setRunning: (v: boolean) => void;
}

export const useStudio = create<StudioState>((set) => ({
  inputs: loadInputs(),
  result: null,
  playIndex: 0,
  running: false,
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
}));
