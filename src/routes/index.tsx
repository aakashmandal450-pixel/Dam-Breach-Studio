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
    if (!result) return null;
    return [
      { k: "Peak Q", v: `${formatNumber(result.Qpeak, 2)} m³/s` },
      { k: "Time to peak", v: `${formatNumber(result.tPeak / 60, 1)} min` },
      { k: "Final Wb", v: `${formatNumber(result.finalWb, 2)} m` },
      { k: "Breach depth", v: `${formatNumber(result.finalDepth, 2)} m` },
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
    downloadText(`${slug(inputs.projectName)}-hydrograph.csv`, resultToCsv(result), "text/csv");
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
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-accent">Formation engine</p>
            <h1 className="font-display text-3xl font-medium tracking-tight">{inputs.projectName}</h1>
            <p className="mt-1 max-w-xl text-sm text-muted-foreground">
              Physically based breach growth — weir / orifice, Wan–Fell erosion, headcut migration, falling
              reservoir.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={run}>
              <Play className="size-4" />
              Run formation
            </Button>
            <Button
              variant={workspaceTab === "results" ? "accent" : "secondary"}
              onClick={() => setWorkspaceTab("results")}
              disabled={!result}
              title={result ? "Open results" : "Run a simulation first"}
            >
              <ChartLine className="size-4" />
              Results
            </Button>
            <Button variant="outline" onClick={exportProject}>
              <Download className="size-4" />
              Export project
            </Button>
            <Button variant="outline" onClick={() => fileRef.current?.click()}>
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

        <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3 sm:flex-row sm:items-end sm:gap-4">
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <Label htmlFor="example-preset">Example case</Label>
            <select
              id="example-preset"
              className="h-10 w-full rounded-md border border-border bg-input px-3 text-sm"
              value={exampleId}
              onChange={(e) => onExampleChange(e.target.value)}
            >
              <option value="custom">Custom (current inputs)</option>
              {EXAMPLES.map((ex) => (
                <option key={ex.id} value={ex.id}>
                  {ex.title}
                </option>
              ))}
            </select>
          </div>
          {exampleId !== "custom" && (
            <p className="max-w-md text-xs text-muted-foreground sm:pb-2">
              {EXAMPLES.find((e) => e.id === exampleId)?.blurb}
            </p>
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
            <CardHeader>
              <CardTitle>Inputs</CardTitle>
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
                  <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
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
                    Export hydrograph CSV
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
