import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChartLine, Download, Play, Settings2, Upload } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { DamSchematic } from "@/components/DamSchematic";
import { ParamForm } from "@/components/ParamForm";
import { ImpulseWavePanel } from "@/components/ImpulseWavePanel";
import { ResultsView } from "@/components/ResultsView";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { EXAMPLES } from "@/lib/breach/examples";
import { runBreachSimulation } from "@/lib/breach/engine";
import type { StudioInputs } from "@/lib/breach/types";
import { cn, downloadText, formatNumber } from "@/lib/utils";
import { useStudio } from "@/store/studio";

export const Route = createFileRoute("/")({ component: SimulatePage });

type WorkspaceTab = "inputs" | "impulse" | "results";

function SimulatePage() {
  const { inputs, result, playIndex, running, setResult, setPlayIndex, setRunning, setInputs } =
    useStudio();
  const fileRef = useRef<HTMLInputElement>(null);
  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("inputs");
  const [exampleId, setExampleId] = useState<string>("custom");

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
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Project</p>
            <p className="break-words text-sm font-medium leading-snug text-foreground">
              {inputs.projectName || "—"}
            </p>
            <p className="text-[10px] leading-snug text-muted-foreground">
              Edit name and examples under Inputs → Project. Mode:{" "}
              <span className="text-foreground">
                {inputs.mode === "piping" ? "piping" : "overtopping"}
              </span>
              {" · "}
              <span className="text-foreground">
                {inputs.damStructure === "zoned"
                  ? "zoned core"
                  : inputs.damStructure === "ice_cored_moraine"
                    ? "ice-cored"
                    : inputs.damStructure === "moraine"
                      ? "moraine"
                      : "homogeneous"}
              </span>
            </p>
          </div>

          {workspaceTab === "inputs" && (
            <div className="overflow-hidden rounded-lg border border-border bg-card">
              <div className="border-b border-border px-3 py-1.5">
                <p className="text-[11px] font-medium text-muted-foreground">
                  Live cross-section — updates with geometry, WL, core, and failure mode
                </p>
              </div>
              <div className="px-1 py-1">
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
              {result.series[Math.min(playIndex, result.series.length - 1)] && (
                <>
                  <span className="text-border">|</span>
                  <Badge tone="accent">
                    {result.series[Math.min(playIndex, result.series.length - 1)].stage}
                  </Badge>
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
            active={workspaceTab === "impulse"}
            onClick={() => setWorkspaceTab("impulse")}
            icon={<ChartLine className="size-3.5" />}
            label="Impulse wave"
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

        {workspaceTab === "impulse" && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">Impulse wave (2-D)</CardTitle>
            </CardHeader>
            <CardContent>
              <ImpulseWavePanel />
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
              <ResultsView
                inputs={inputs}
                result={result}
                playIndex={playIndex}
                running={running}
                setPlayIndex={setPlayIndex}
                setRunning={setRunning}
                onEditInputs={() => setWorkspaceTab("inputs")}
                onRerun={run}
              />
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
