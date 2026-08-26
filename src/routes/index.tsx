import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ChartLine, Download, Play, Settings2, Upload } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { DamSchematic } from "@/components/DamSchematic";
import { ParamForm } from "@/components/ParamForm";
import { ResultCharts } from "@/components/ResultCharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { EXAMPLES } from "@/lib/breach/examples";
import { resultToCsv, runBreachSimulation } from "@/lib/breach/engine";
import type { StudioInputs } from "@/lib/breach/types";
import { cn, downloadText, formatNumber } from "@/lib/utils";
import { useStudio } from "@/store/studio";

export const Route = createFileRoute("/")({ component: SimulatePage });

type WorkspaceTab = "inputs" | "results";

function SimulatePage() {
  const { inputs, result, playIndex, running, setResult, setPlayIndex, setRunning, setInputs } =
    useStudio();
  const fileRef = useRef<HTMLInputElement>(null);
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("inputs");
  const [exampleId, setExampleId] = useState<string>("custom");

  const step = result?.series[Math.min(playIndex, (result?.series.length ?? 1) - 1)] ?? null;

  const stats = useMemo(() => {
    if (!result || result.series.length === 0) return null;
    const first = result.series[0];
    const last = result.series[result.series.length - 1];
    const volReleased = Math.max(0, first.V - last.V);
    const tauMax = result.series.reduce((m, s) => Math.max(m, s.tau), 0);
    const tBreach =
      result.tEmpty ??
      (last.stage === "empty" ? last.t : result.series[result.series.length - 1].t);

    return [
      { k: "Peak discharge Qp", v: `${formatNumber(result.Qpeak, 2)} m³/s` },
      { k: "Time to peak", v: `${formatNumber(result.tPeak / 60, 1)} min` },
      { k: "Time to empty / end", v: `${formatNumber(tBreach / 60, 1)} min` },
      {
        k: "Headcut through C",
        v:
          result.tHeadcutBreach == null
            ? "—"
            : `${formatNumber(result.tHeadcutBreach / 60, 1)} min`,
      },
      {
        k: "Roof collapse",
        v: result.tCollapse == null ? "—" : `${formatNumber(result.tCollapse / 60, 1)} min`,
      },
      { k: "Volume released", v: `${formatNumber(volReleased, 0)} m³` },
      { k: "Final Wb", v: `${formatNumber(result.finalWb, 2)} m` },
      { k: "Breach depth", v: `${formatNumber(result.finalDepth, 2)} m` },
      { k: "Max shear τ", v: `${formatNumber(tauMax, 1)} Pa` },
      { k: "Compute", v: `${formatNumber(result.elapsedMs, 0)} ms` },
    ];
  }, [result]);

  useEffect(() => {
    if (!running || !result) return;
    const id = window.setInterval(() => {
      useStudio.setState((s) => {
        if (!s.result) return { running: false };
        const next = Math.min(s.playIndex + 1, s.result.series.length - 1);
        return { playIndex: next, running: next < s.result.series.length - 1 };
      });
    }, 40);
    return () => window.clearInterval(id);
  }, [running, result]);

  function run() {
    const next = runBreachSimulation(inputs);
    setResult(next);
    setPlayIndex(0);
    setRunning(true);
    setWorkspaceTab("results");
  }

  function exportProject() {
    downloadText(
      `${slug(inputs.projectName)}.json`,
      JSON.stringify(inputs, null, 2),
      "application/json",
    );
  }

  function exportCsv() {
    if (!result) return;
    downloadText(`${slug(inputs.projectName)}-series.csv`, resultToCsv(result), "text/csv");
  }

  function exportSummary() {
    if (!result || !stats) return;
    const payload = {
      project: inputs.projectName,
      mode: inputs.mode,
      peakQ_m3s: result.Qpeak,
      timeToPeak_min: result.tPeak / 60,
      timeToEmpty_min: result.tEmpty != null ? result.tEmpty / 60 : null,
      tHeadcutBreach_min: result.tHeadcutBreach != null ? result.tHeadcutBreach / 60 : null,
      tRoofCollapse_min: result.tCollapse != null ? result.tCollapse / 60 : null,
      finalWb_m: result.finalWb,
      breachDepth_m: result.finalDepth,
      stats: Object.fromEntries(stats.map((s) => [s.k, s.v])),
      warnings: result.warnings,
    };
    downloadText(
      `${slug(inputs.projectName)}-summary.json`,
      JSON.stringify(payload, null, 2),
      "application/json",
    );
  }

  function onImport(file: File) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result)) as StudioInputs;
        setInputs({ ...inputs, ...parsed });
        setExampleId("custom");
      } catch {
        /* ignore malformed */
      }
    };
    reader.readAsText(file);
  }

  function onExampleChange(id: string) {
    setExampleId(id);
    if (id === "custom") return;
    const ex = EXAMPLES.find((e) => e.id === id);
    if (ex) setInputs(ex.inputs);
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0">
            <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-accent">Formation engine</p>
            <h1 className="font-display truncate text-xl font-medium tracking-tight md:text-2xl">
              {inputs.projectName}
            </h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={run}>
              <Play className="size-4" />
              Run formation
            </Button>
            <Button
              size="sm"
              variant={workspaceTab === "results" ? "accent" : "secondary"}
              onClick={() => setWorkspaceTab("results")}
              disabled={!result}
            >
              <ChartLine className="size-4" />
              Results
            </Button>
            <Button size="sm" variant="outline" onClick={exportProject}>
              <Download className="size-4" />
              Project
            </Button>
            <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()}>
              <Upload className="size-4" />
              Import
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept="application/json"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onImport(f);
                e.target.value = "";
              }}
            />
          </div>
        </div>

        <div className="grid gap-3 lg:grid-cols-[minmax(0,14rem)_minmax(0,1fr)]">
          <div className="flex flex-col gap-1.5 rounded-lg border border-border bg-card p-2.5">
            <Label htmlFor="example-preset" className="text-[11px]">
              Example case
            </Label>
            <select
              id="example-preset"
              className="h-8 w-full rounded-md border border-border bg-input px-2 text-xs"
              value={exampleId}
              onChange={(e) => onExampleChange(e.target.value)}
            >
              <option value="custom">Custom</option>
              {EXAMPLES.map((ex) => (
                <option key={ex.id} value={ex.id}>
                  {ex.title}
                </option>
              ))}
            </select>
            {exampleId !== "custom" && (
              <p className="line-clamp-3 text-[10px] leading-snug text-muted-foreground">
                {EXAMPLES.find((e) => e.id === exampleId)?.blurb}
              </p>
            )}
          </div>

          {workspaceTab === "inputs" && (
            <div className="overflow-hidden rounded-lg border border-border bg-card">
              <div className="border-b border-border px-3 py-1.5">
                <p className="text-[11px] font-medium text-muted-foreground">
                  Input schematic — symbols match the parameter tabs (Hb, C, Z1, Z2, Wb, WL, R, x_h)
                </p>
              </div>
              <div className="max-h-[11rem] overflow-hidden px-1">
                <DamSchematic inputs={inputs} step={null} />
              </div>
            </div>
          )}

          {workspaceTab === "results" && result && (
            <div className="flex flex-wrap items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-xs text-muted-foreground">
              <span>
                Qp <strong className="text-foreground">{formatNumber(result.Qpeak, 1)}</strong> m³/s
              </span>
              <span className="text-border">|</span>
              <span>
                t_peak <strong className="text-foreground">{formatNumber(result.tPeak / 60, 1)}</strong> min
              </span>
              <span className="text-border">|</span>
              <span>
                Wb <strong className="text-foreground">{formatNumber(result.finalWb, 2)}</strong> m
              </span>
              {step && (
                <>
                  <span className="text-border">|</span>
                  <Badge tone="accent">{step.stage}</Badge>
                </>
              )}
            </div>
          )}
        </div>

        <div
          role="tablist"
          aria-label="Workspace"
          className="flex gap-1 rounded-lg border border-border bg-muted/40 p-1"
        >
          <WorkspaceTabButton
            active={workspaceTab === "inputs"}
            onClick={() => setWorkspaceTab("inputs")}
            icon={<Settings2 className="size-3.5" />}
            label="Inputs"
          />
          <WorkspaceTabButton
            active={workspaceTab === "results"}
            onClick={() => setWorkspaceTab("results")}
            icon={<ChartLine className="size-3.5" />}
            label="Results & simulation"
            badge={result ? undefined : "empty"}
          />
        </div>

        {workspaceTab === "inputs" && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Inputs</CardTitle>
            </CardHeader>
            <CardContent>
              <ParamForm />
              <div className="mt-6 flex flex-wrap gap-2 border-t border-border pt-4">
                <Button onClick={run}>
                  <Play className="size-4" />
                  Run formation
                </Button>
                <Button variant="secondary" onClick={() => setWorkspaceTab("results")} disabled={!result}>
                  <ChartLine className="size-4" />
                  Go to results
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {workspaceTab === "results" && (
          <div className="flex flex-col gap-4">
            {!result ? (
              <Card>
                <CardContent className="flex flex-col items-start gap-3 py-10">
                  <p className="text-sm text-muted-foreground">
                    No run yet. Set parameters on the Inputs tab, then press <strong>Run formation</strong>.
                  </p>
                  <Button onClick={() => setWorkspaceTab("inputs")} variant="secondary">
                    <Settings2 className="size-4" />
                    Back to inputs
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <>
                <Card>
                  <CardHeader className="flex-row items-center justify-between">
                    <CardTitle>Simulation — cross-section</CardTitle>
                    {step && <Badge tone="accent">{step.stage}</Badge>}
                  </CardHeader>
                  <CardContent>
                    <DamSchematic inputs={inputs} step={step} />
                    {result.series.length > 1 && (
                      <div className="mt-4 flex flex-col gap-2">
                        <Slider
                          min={0}
                          max={result.series.length - 1}
                          step={1}
                          value={[playIndex]}
                          onValueChange={(v) => {
                            setRunning(false);
                            setPlayIndex(v[0] ?? 0);
                          }}
                        />
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{((step?.t ?? 0) / 60).toFixed(1)} min</span>
                          <button
                            type="button"
                            className="text-accent"
                            onClick={() => setRunning(!running)}
                          >
                            {running ? "Pause" : "Play"}
                          </button>
                          <span>Q = {formatNumber(step?.Q ?? 0, 2)} m³/s</span>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {stats && (
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
                    {stats.map((s) => (
                      <div key={s.k} className="rounded-lg border border-border bg-card px-3 py-3">
                        <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{s.k}</p>
                        <p className="font-mono text-sm tabular-nums">{s.v}</p>
                      </div>
                    ))}
                  </div>
                )}

                {result.warnings.length > 0 && (
                  <div className="rounded-lg border border-border bg-card px-4 py-3 text-sm text-warn">
                    {result.warnings.map((w) => (
                      <p key={w}>{w}</p>
                    ))}
                  </div>
                )}

                <ResultCharts result={result} playIndex={playIndex} />

                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={exportCsv}>
                    <Download className="size-4" />
                    Export time-series CSV
                  </Button>
                  <Button variant="outline" size="sm" onClick={exportSummary}>
                    <Download className="size-4" />
                    Export summary JSON
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => setWorkspaceTab("inputs")}>
                    <Settings2 className="size-4" />
                    Edit inputs
                  </Button>
                  <Button size="sm" onClick={run}>
                    <Play className="size-4" />
                    Re-run
                  </Button>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}

function WorkspaceTabButton({
  active,
  onClick,
  icon,
  label,
  badge,
}: {
  active: boolean;
  onClick: () => void;
  icon: ReactNode;
  label: string;
  badge?: "empty";
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "inline-flex flex-1 items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
      )}
    >
      {icon}
      {label}
      {badge === "empty" && !active && (
        <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">no run</span>
      )}
    </button>
  );
}

function slug(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "project";
}
