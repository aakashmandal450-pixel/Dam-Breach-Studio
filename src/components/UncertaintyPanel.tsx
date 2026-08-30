import { useState } from "react";
import { Button } from "@/components/ui/button";
import { runUncertaintyBand, type UncertaintyBand } from "@/lib/breach/uncertainty";
import type { StudioInputs } from "@/lib/breach/types";
import { formatNumber } from "@/lib/utils";

export function UncertaintyPanel({ inputs }: { inputs: StudioInputs }) {
  const [band, setBand] = useState<UncertaintyBand | null>(null);
  const [busy, setBusy] = useState(false);

  function run() {
    setBusy(true);
    // yield so UI can paint
    window.setTimeout(() => {
      try {
        setBand(runUncertaintyBand(inputs, inputs.uncertaintyDeltaI ?? 0.5));
      } finally {
        setBusy(false);
      }
    }, 20);
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-medium">Uncertainty band on I</p>
          <p className="text-xs text-muted-foreground">
            Three formation runs at I−ΔI, I, I+ΔI (ΔI = {inputs.uncertaintyDeltaI ?? 0.5}). Peak discharge is the main screening metric.
          </p>
        </div>
        <Button type="button" size="sm" onClick={run} disabled={busy}>
          {busy ? "Running…" : "Compute Qp band"}
        </Button>
      </div>
      {band && (
        <div className="space-y-2 text-sm">
          <div className="grid grid-cols-3 gap-2 text-center">
            <Stat label={`Qp (I=${band.I_low.toFixed(2)})`} value={`${formatNumber(band.Qp_low, 1)} m³/s`} hint="more erodible" />
            <Stat label={`Qp (I=${band.I_base.toFixed(2)})`} value={`${formatNumber(band.Qp_base, 1)} m³/s`} hint="base" />
            <Stat label={`Qp (I=${band.I_high.toFixed(2)})`} value={`${formatNumber(band.Qp_high, 1)} m³/s`} hint="more resistant" />
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">{band.note}</p>
          <p className="text-xs text-muted-foreground">
            Time to peak (base): {formatNumber(band.tPeak_base / 60, 1)} min
            {band.tHeadcut_base != null
              ? ` · Headcut through C: ${formatNumber(band.tHeadcut_base / 60, 1)} min`
              : " · Headcut breakthrough: —"}
          </p>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/30 px-2 py-2">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className="font-mono text-sm font-medium">{value}</p>
      <p className="text-[10px] text-muted-foreground">{hint}</p>
    </div>
  );
}
