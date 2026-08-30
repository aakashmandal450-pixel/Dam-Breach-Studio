import { useMemo } from "react";
import { Info } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useStudio } from "@/store/studio";
import type { InflowIntervalUnit, InflowSeriesPoint } from "@/lib/breach/types";
import { buildInflowSeriesGrid, intervalToSeconds } from "@/lib/breach/inflowSeries";
import { formatNumber } from "@/lib/utils";

/**
 * Discrete inflow hydrograph Q_in(t) editor.
 * User sets duration + interval (+ unit), generates rows, edits Q, enables series for the run.
 */
export function InflowSeriesPanel() {
  const { inputs, setInput } = useStudio();
  const unit = inputs.inflowSeriesUnit ?? "h";
  const duration = inputs.inflowSeriesDuration ?? 6;
  const interval = inputs.inflowSeriesInterval ?? 1;
  const series = inputs.inflowSeries ?? [];
  const enabled = inputs.inflowSeriesEnabled ?? false;

  const dtSec = intervalToSeconds(interval, unit);
  const nRows = useMemo(() => {
    if (dtSec <= 0) return 0;
    const T = intervalToSeconds(duration, unit);
    return Math.min(500, Math.floor(T / dtSec) + 1);
  }, [duration, interval, unit, dtSec]);

  function generate() {
    const pts = buildInflowSeriesGrid(duration, interval, unit, inputs.inflowM3s);
    setInput("inflowSeries", pts);
    setInput("inflowSeriesEnabled", true);
  }

  function clearSeries() {
    setInput("inflowSeries", []);
    setInput("inflowSeriesEnabled", false);
  }

  function setPoint(i: number, Q: number) {
    const next = series.map((p, j) => (j === i ? { ...p, Q: Math.max(0, Q) } : p));
    setInput("inflowSeries", next);
  }

  function formatTime(sec: number): string {
    if (unit === "s") return `${sec.toFixed(0)} s`;
    if (unit === "min") return `${(sec / 60).toFixed(2)} min`;
    return `${(sec / 3600).toFixed(3)} h`;
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs text-muted-foreground leading-relaxed">
        Build a discrete inflow series <span className="font-mono">Qin(t)</span> used by the
        formation engine instead of the constant inflow. Example: duration 6 h, interval 1 h →
        rows at 0, 1, 2, …, 6 h. Edit each discharge; linear interpolation is used between nodes.
      </p>

      <div className="flex flex-wrap items-end gap-2">
        <div className="flex flex-col gap-1">
          <Label className="text-xs">Max duration</Label>
          <div className="relative">
            <Input
              type="number"
              step={0.1}
              className="h-8 w-24 pr-2 text-sm"
              value={duration}
              onChange={(e) => setInput("inflowSeriesDuration", Number(e.target.value))}
            />
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <Label className="text-xs">Time interval</Label>
          <Input
            type="number"
            step={0.1}
            className="h-8 w-24 text-sm"
            value={interval}
            onChange={(e) => setInput("inflowSeriesInterval", Number(e.target.value))}
          />
        </div>
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-1">
            <Label className="text-xs">Unit</Label>
            <Tooltip>
              <TooltipTrigger asChild>
                <button type="button" className="text-muted-foreground" aria-label="About unit">
                  <Info className="size-3" />
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-xs text-xs">
                Applies to both duration and interval. Seconds for short wave pulses; hours for
                cascading GLOF or multi-hour flood inflow.
              </TooltipContent>
            </Tooltip>
          </div>
          <select
            className="h-8 rounded-md border border-border bg-input px-2 text-sm"
            value={unit}
            onChange={(e) => setInput("inflowSeriesUnit", e.target.value as InflowIntervalUnit)}
          >
            <option value="s">seconds (s)</option>
            <option value="min">minutes (min)</option>
            <option value="h">hours (h)</option>
          </select>
        </div>
        <Button type="button" size="sm" onClick={generate}>
          Generate table (~{nRows} rows)
        </Button>
        <Button type="button" size="sm" variant="secondary" onClick={clearSeries}>
          Clear
        </Button>
      </div>

      <div className="flex items-center gap-2">
        <label className="flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setInput("inflowSeriesEnabled", e.target.checked)}
          />
          Use series in formation run (overrides constant inflow)
        </label>
        {!enabled && (
          <span className="text-[10px] text-muted-foreground">
            Constant Qin = {formatNumber(inputs.inflowM3s, 2)} m³/s
          </span>
        )}
      </div>

      {series.length > 0 && (
        <div className="max-h-64 overflow-auto rounded-md border border-border">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-muted/90">
              <tr>
                <th className="px-2 py-1.5 text-left font-medium">#</th>
                <th className="px-2 py-1.5 text-left font-medium">Time</th>
                <th className="px-2 py-1.5 text-left font-medium">Qin (m³/s)</th>
              </tr>
            </thead>
            <tbody>
              {series.map((pt: InflowSeriesPoint, i: number) => (
                <tr key={i} className="border-t border-border/60">
                  <td className="px-2 py-1 text-muted-foreground">{i + 1}</td>
                  <td className="px-2 py-1 font-mono">{formatTime(pt.timeSec)}</td>
                  <td className="px-2 py-1">
                    <Input
                      type="number"
                      step={0.1}
                      className="h-7 w-28 text-sm"
                      value={pt.Q}
                      onChange={(e) => setPoint(i, Number(e.target.value))}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {series.length === 0 && (
        <p className="text-[11px] text-muted-foreground">
          No series yet. Set duration and interval, then Generate table. Fill Qin values for each
          time node (e.g. cascading flood or wave-overtopping pulse).
        </p>
      )}
    </div>
  );
}
