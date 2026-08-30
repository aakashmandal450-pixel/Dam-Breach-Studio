import { useMemo } from "react";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useStudio } from "@/store/studio";
import {
  LAKE_VOLUME_FORMULAS,
  estimateLakeVolume,
  freeboard,
  type LakeVolumeFormulaId,
} from "@/lib/lake/volume";
import { formatNumber } from "@/lib/utils";

export function LakeVolumePanel() {
  const { inputs, setInput } = useStudio();
  const formulaId = (inputs.lakeVolumeFormula ?? "manual") as LakeVolumeFormulaId;
  const estimated = useMemo(
    () => estimateLakeVolume(inputs.surfaceAreaHa, formulaId),
    [inputs.surfaceAreaHa, formulaId],
  );
  const fb = freeboard(inputs.crestElev, inputs.initialWL);
  const formula = LAKE_VOLUME_FORMULAS.find((f) => f.id === formulaId)!;

  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Glacial / moraine lake volume from area
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="lakeVolumeFormula">V(A) formula</Label>
          <select
            id="lakeVolumeFormula"
            className="h-10 rounded-md border border-border bg-input px-3 text-sm"
            value={formulaId}
            onChange={(e) => setInput("lakeVolumeFormula", e.target.value as LakeVolumeFormulaId)}
          >
            {LAKE_VOLUME_FORMULAS.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} — {f.region}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col justify-end gap-1.5">
          <p className="text-sm text-muted-foreground">
            Estimated V ={" "}
            <span className="font-medium text-foreground">
              {formulaId === "manual" ? "—" : `${formatNumber(estimated, 0)} m³`}
            </span>
          </p>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={formulaId === "manual" || estimated <= 0}
            onClick={() => setInput("volumeM3", Math.round(estimated))}
          >
            Apply to storage
          </Button>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">{formula.note}</p>
      <p className="mt-1 text-xs text-muted-foreground">
        Freeboard f = crest − WL ={" "}
        <span className={fb >= 0 ? "text-foreground" : "text-destructive font-medium"}>
          {formatNumber(fb, 2)} m
        </span>
        {fb < 0 ? " (already overtopping)" : ""}
      </p>
    </div>
  );
}
