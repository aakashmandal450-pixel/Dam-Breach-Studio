import type { SimResult, StudioInputs } from "@/lib/breach/types";
import {
  cellValue,
  computeBreachSummary,
  seriesColumns,
  type ExportKind,
} from "@/lib/breach/resultMetrics";

function slug(s: string) {
  return (s || "run").replace(/[^\w\-]+/g, "_").slice(0, 48);
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Draw a simple line chart to PNG for embedding in the workbook. */
function lineChartPng(
  points: { x: number; y: number }[],
  opts: { title: string; xLabel: string; yLabel: string; width?: number; height?: number },
): Promise<ArrayBuffer> {
  const W = opts.width ?? 640;
  const H = opts.height ?? 360;
  const pad = { l: 56, r: 20, t: 36, b: 44 };
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d");
  if (!ctx || points.length < 2) {
    return Promise.resolve(new ArrayBuffer(0));
  }
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, W, H);
  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const x0 = Math.min(...xs);
  const x1 = Math.max(...xs);
  const y0 = Math.min(0, ...ys);
  const y1 = Math.max(...ys) * 1.05 || 1;
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;
  const sx = (x: number) => pad.l + ((x - x0) / (x1 - x0 || 1)) * plotW;
  const sy = (y: number) => pad.t + plotH - ((y - y0) / (y1 - y0 || 1)) * plotH;

  ctx.strokeStyle = "#d4cdc0";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const yy = pad.t + (plotH * i) / 4;
    ctx.beginPath();
    ctx.moveTo(pad.l, yy);
    ctx.lineTo(W - pad.r, yy);
    ctx.stroke();
  }
  ctx.strokeStyle = "#1a1814";
  ctx.strokeRect(pad.l, pad.t, plotW, plotH);

  ctx.beginPath();
  ctx.strokeStyle = "#245460";
  ctx.lineWidth = 2;
  points.forEach((p, i) => {
    const X = sx(p.x);
    const Y = sy(p.y);
    if (i === 0) ctx.moveTo(X, Y);
    else ctx.lineTo(X, Y);
  });
  ctx.stroke();

  ctx.fillStyle = "#1a1814";
  ctx.font = "12px system-ui, sans-serif";
  ctx.fillText(opts.title, pad.l, 22);
  ctx.font = "10px system-ui, sans-serif";
  ctx.fillStyle = "#666";
  ctx.fillText(opts.xLabel, pad.l + plotW / 2 - 20, H - 12);
  ctx.save();
  ctx.translate(14, pad.t + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText(opts.yLabel, 0, 0);
  ctx.restore();
  ctx.fillText(y1.toFixed(1), 4, pad.t + 8);
  ctx.fillText(y0.toFixed(1), 4, pad.t + plotH);

  return new Promise((resolve) => {
    canvas.toBlob(
      (b) => {
        if (!b) {
          resolve(new ArrayBuffer(0));
          return;
        }
        b.arrayBuffer().then(resolve);
      },
      "image/png",
    );
  });
}

type ChartSpec = {
  title: string;
  xLabel: string;
  yLabel: string;
  points: { x: number; y: number }[];
};

function chartsForKind(result: SimResult, inputs: StudioInputs, kind: ExportKind): ChartSpec[] {
  const s = result.series;
  if (kind === "hydrograph" || kind === "summary" || kind === "full") {
    return [
      {
        title: "Outflow hydrograph Q(t) — total",
        xLabel: "t (h)",
        yLabel: "Q (m³/s)",
        points: s.map((p) => ({ x: p.t / 3600, y: p.Q })),
      },
    ];
  }
  if (kind === "rating") {
    // Head vs breach discharge — not time-based, so points are sorted by head
    // rather than by t, matching a classic rating-curve plot.
    const pts = s
      .map((p) => ({ x: Math.max(p.WL - p.zb, 0), y: Math.max(p.Q - inputs.spillwayQ, 0) }))
      .sort((a, b) => a.x - b.x);
    return [
      {
        title: "Rating curve — head vs breach discharge",
        xLabel: "head (m)",
        yLabel: "Q breach (m³/s)",
        points: pts,
      },
    ];
  }
  if (kind === "breach") {
    return [
      {
        title: "Breach base width Wb(t)",
        xLabel: "t (h)",
        yLabel: "Wb (m)",
        points: s.map((p) => ({ x: p.t / 3600, y: p.Wb })),
      },
    ];
  }
  if (kind === "reservoir") {
    return [
      {
        title: "Reservoir water level WL(t)",
        xLabel: "t (h)",
        yLabel: "WL (m)",
        points: s.map((p) => ({ x: p.t / 3600, y: p.WL })),
      },
    ];
  }
  if (kind === "diagnostics") {
    return [
      {
        title: "Applied shear τ(t)",
        xLabel: "t (h)",
        yLabel: "τ (Pa)",
        points: s.map((p) => ({ x: p.t / 3600, y: p.tau })),
      },
    ];
  }
  return [];
}

/**
 * Build and download an .xlsx workbook for the selected result kind.
 * Requires: npm install exceljs
 * Sheets: Meta | Summary (when relevant) | Data | Chart (embedded PNG of primary series).
 */
export async function downloadResultExcel(
  result: SimResult,
  inputs: StudioInputs,
  kind: ExportKind,
): Promise<void> {
  const ExcelJS = await import("exceljs");
  const wb = new ExcelJS.Workbook();
  wb.creator = "Dam Breach Studio";
  wb.created = new Date();

  const meta = wb.addWorksheet("Meta");
  meta.addRow(["Project", inputs.projectName]);
  meta.addRow(["Failure mode", inputs.mode]);
  meta.addRow(["Dam structure", inputs.damStructure]);
  meta.addRow(["Exported", new Date().toISOString()]);
  meta.addRow(["Kind", kind]);
  meta.addRow(["Units", "SI (m, m³/s, Pa, s)"]);

  const m = computeBreachSummary(result, inputs);
  if (kind === "summary" || kind === "full") {
    const sum = wb.addWorksheet("Summary");
    sum.addRow(["Metric", "Value", "Unit", "BREACH-GUI analogue"]);
    const rows: [string, string | number, string, string][] = [
      ["Peak discharge Qp", m.Qpeak, "m³/s", "QP / QPB"],
      ["Time to peak TP", m.tPeak_min, "min", "TP"],
      ["Failure start TB", m.tB_min ?? "—", "min", "TB"],
      ["Rising limb TRS", m.tRS_min ?? "—", "min", "TRS = TP−TB"],
      ["Roof collapse", m.tCollapse_s != null ? m.tCollapse_s / 60 : "—", "min", "collapse mode"],
      ["Headcut through C", m.tHeadcutBreach_s != null ? m.tHeadcutBreach_s / 60 : "—", "min", "—"],
      ["Time to empty", m.tEmpty_s != null ? m.tEmpty_s / 60 : "—", "min", "draining"],
      ["Volume released", m.volumeReleased_m3, "m³", "—"],
      ["Final Wb", m.finalWb_m, "m", "BO"],
      ["Final Wtop", m.finalWtop_m, "m", "BT / BRW"],
      ["Final breach depth", m.finalDepth_m, "m", "BRD"],
      ["Final WL", m.finalWL_m, "m", "HY"],
      ["Final zb", m.finalZb_m, "m", "HC"],
      ["Q at t=0", m.Q0_m3s, "m³/s", "QO"],
      ["Max shear τ", m.maxTau_Pa, "Pa", "—"],
      ["Side slope at peak Z", m.peakSideSlope ?? "—", "H:V", "Z"],
      ["Velocity at peak", m.peakVelocity_ms ?? "—", "m/s", "—"],
    ];
    rows.forEach((r) => sum.addRow(r));
    sum.getRow(1).font = { bold: true };
    sum.columns.forEach((c) => {
      c.width = 22;
    });
  }

  if (kind !== "summary") {
    const cols = seriesColumns(kind === "full" ? "full" : kind);
    const data = wb.addWorksheet("Data");
    data.addRow(cols.map((c) => `${c.header} (${c.unit})`));
    for (const step of result.series) {
      data.addRow(cols.map((c) => cellValue(step, c.key, inputs.spillwayQ)));
    }
    data.getRow(1).font = { bold: true };
    data.columns.forEach((c) => {
      c.width = 14;
    });
  }

  // Chart image sheet
  const chartSpecs = chartsForKind(result, inputs, kind);
  if (chartSpecs.length > 0) {
    const ch = wb.addWorksheet("Chart");
    ch.getCell("A1").value = chartSpecs[0].title;
    ch.getCell("A1").font = { bold: true, size: 12 };
    ch.getCell("A2").value =
      "Embedded chart image (open Data sheet to build a native Excel chart: select columns → Insert → Charts → Line).";
    try {
      const png = await lineChartPng(chartSpecs[0].points, chartSpecs[0]);
      if (png.byteLength > 0) {
        const imgId = wb.addImage({
          buffer: png,
          extension: "png",
        });
        ch.addImage(imgId, {
          tl: { col: 0, row: 3 },
          ext: { width: 640, height: 360 },
        });
      }
    } catch {
      ch.getCell("A3").value = "Chart image could not be generated in this browser.";
    }
  }

  const buf = await wb.xlsx.writeBuffer();
  const blob = new Blob([buf], {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
  const name = `${slug(inputs.projectName)}_${kind}.xlsx`;
  downloadBlob(blob, name);
}

/**
 * Serialize a rendered chart's SVG into a small standalone HTML file and
 * trigger a download. Recharts renders real SVG in the DOM, so no chart
 * library or server round-trip is needed — we just wrap the live markup.
 */
export function downloadChartHtml(container: HTMLElement | null, title: string, projectName: string): void {
  if (!container) return;
  const svgs = Array.from(container.querySelectorAll("svg"));
  if (svgs.length === 0) return;

  const chartWraps = svgs.map((svg) => `<div class="chart-wrap">${svg.outerHTML}</div>`).join("\n  ");
  const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>${title} — ${projectName}</title>
<style>
  body { font-family: system-ui, sans-serif; background: #fbf8f2; color: #1a1814; margin: 0; padding: 24px; }
  h1 { font-size: 16px; margin: 0 0 4px; }
  p { font-size: 12px; color: #6b6459; margin: 0 0 20px; }
  .chart-wrap { background: #ffffff; border: 1px solid #d4cdc0; border-radius: 8px; padding: 16px; max-width: 900px; margin-bottom: 16px; }
  svg { width: 100%; height: auto; }
</style>
</head>
<body>
  <h1>${title}</h1>
  <p>${projectName} — exported from Dam Breach Studio</p>
  ${chartWraps}
</body>
</html>`;

  const blob = new Blob([html], { type: "text/html" });
  downloadBlob(blob, `${slug(projectName)}_${slug(title)}.html`);
}
