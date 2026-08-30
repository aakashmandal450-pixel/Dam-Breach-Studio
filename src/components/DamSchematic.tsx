import type { SimStep, StudioInputs } from "@/lib/breach/types";

interface Props {
  inputs: StudioInputs;
  step: SimStep | null;
}

/**
 * Engineering cross-section (inputs + results).
 * - Solid dam; water only upstream before / without an open breach cut
 * - Zoned (core + shell): hashed core, small internal labels (ct, Zc, cb)
 * - Hb and Hc dimensioned on the right
 * - WL near left water–face intersection; "overtopping" far left
 * - No project name on the figure
 */
export function DamSchematic({ inputs, step }: Props) {
  const Hb = Math.max(inputs.crestElev - inputs.baseElev, 0.1);
  const W = 760;
  const H = 260;
  const bed = 226;
  const crestY = 42;
  const damH = bed - crestY;
  const crestW = Math.max(40, Math.min(100, 20 + inputs.crestWidth * 5));
  const upRun = Math.max(55, inputs.zUp * damH * 0.28);
  const dnRun = Math.max(50, inputs.zDown * damH * 0.28);
  const cx = 400;
  const crestL = cx - crestW / 2;
  const crestR = cx + crestW / 2;
  const toeL = crestL - upRun;
  const toeR = crestR + dnRun;

  const elevToY = (elev: number) => {
    const t = (inputs.crestElev - elev) / Hb;
    return crestY + clamp(t, 0, 1.05) * damH;
  };

  const WL = step?.WL ?? inputs.initialWL;
  const waterY = elevToY(WL);
  const zbY = elevToY(step?.zb ?? (inputs.mode === "piping" ? inputs.pipeInvert : inputs.crestElev));
  const Wb = step?.Wb ?? inputs.initialNotchWidth;
  const WbPx = Math.min(140, Math.max(8, (Wb / Math.max(inputs.crestLength, 1)) * 180));
  const Rval = step?.R ?? inputs.initialPipeRadius;
  const pipeR = Math.max(3, (Rval / Hb) * damH * 1.8);
  const pipeY = elevToY(inputs.pipeInvert);
  const stage = step?.stage ?? (inputs.mode === "overtopping" ? "open" : "piping");

  const hasOpenBreach =
    !!step &&
    (stage === "open" || stage === "empty" || stage === "headcut") &&
    (step.Wb > inputs.initialNotchWidth * 1.15 || (step.zb ?? inputs.crestElev) < inputs.crestElev - 0.15);
  const inHeadcut = stage === "headcut";
  const inPiping = !hasOpenBreach && (stage === "piping" || (inputs.mode === "piping" && !step));

  const C = Math.max(inputs.crestWidth, 0.5);
  const xH = clamp(step?.xHeadcut ?? 0, 0, C);
  const headcutX = crestR - (xH / C) * crestW;
  const freeboardVal = inputs.crestElev - WL;
  const fmt = (v: number, d = 1) => (Number.isFinite(v) ? v.toFixed(d) : "—");

  // Zoned core only (core + shell) — real user-entered geometry, not a heuristic.
  // Core height is a FRACTION of dam height Hb, so it always scales proportionally
  // with the dam whenever Hb changes (crest/base elevation edits included).
  const showCore = inputs.damStructure === "zoned";
  const Zc = showCore ? Math.max(0.02, inputs.coreSideSlope ?? 0.5) : 0;
  const HcM = showCore ? clamp((inputs.coreHeightFraction ?? 0.85) * Hb, 0.1, Hb) : 0;
  const ctM = showCore ? Math.max(0.2, inputs.coreTopWidth ?? 2.5) : 0;
  const cbM = showCore ? ctM + 2 * Zc * HcM : 0;
  const coreTopY = elevToY(inputs.baseElev + HcM);
  const scaleX = crestW / Math.max(C, 0.5);
  // Safety clamp: keep the core's base from ever exceeding the dam's own base
  // width on screen, regardless of how extreme coreTopWidth/coreSideSlope get.
  const maxBasePx = (toeR - toeL) * 0.94;
  const cbPx = Math.min(cbM * scaleX, maxBasePx);
  const ctPx = Math.min(ctM * scaleX, cbPx * 0.92);
  const coreTopL = cx - ctPx / 2;
  const coreTopR = cx + ctPx / 2;
  const coreBotL = cx - cbPx / 2;
  const coreBotR = cx + cbPx / 2;

  // Water: upstream pool only — never fills dam body
  const waterLeft = 24;
  let waterPts: string;
  let sheetPts: string | null = null;
  let spillPts: string | null = null;

  if (hasOpenBreach && waterY < zbY + 4) {
    waterPts = `${waterLeft},${bed} ${waterLeft},${waterY} ${cx - WbPx / 2},${Math.min(waterY, zbY)} ${cx + WbPx / 2},${Math.min(waterY, zbY)} ${cx + WbPx / 2 + 28},${bed}`;
  } else {
    // Pool bounded by the upstream face only — intersect water line with upstream slope.
    // t=0 means water at the crest (top of slope, x=crestL); t=1 means water at the
    // base (bottom of slope, x=toeL). faceX must move toward crestL as t -> 0.
    const t = clamp((waterY - crestY) / damH, 0, 1);
    const faceX = crestL - t * upRun;
    waterPts = `${waterLeft},${bed} ${waterLeft},${waterY} ${faceX},${waterY} ${toeL},${bed}`;

    if (freeboardVal <= 0.02) {
      // Thin band sitting on the crest itself...
      const bandHalf = 2.4;
      sheetPts = `${crestL},${crestY - bandHalf} ${crestR},${crestY - bandHalf} ${crestR},${crestY + bandHalf} ${crestL},${crestY + bandHalf}`;

      // ...plus a short spill ribbon that runs exactly along the downstream slope
      // direction (parallel edges), so it reads as a thin sheet on the face rather
      // than a wedge cutting back across the crest.
      const s = 0.22; // fraction of the slope length the spill travels
      const len = Math.sqrt(dnRun * dnRun + damH * damH) || 1;
      const ux = dnRun / len;
      const uy = damH / len;
      const px = -uy;
      const py = ux;
      const halfT = 3;
      const ax = crestR;
      const ay = crestY;
      const bx = crestR + dnRun * s;
      const by = crestY + damH * s;
      spillPts = `${ax + px * halfT},${ay + py * halfT} ${bx + px * halfT},${by + py * halfT} ${bx - px * halfT},${by - py * halfT} ${ax - px * halfT},${ay - py * halfT}`;
    }
  }

  // WL label near water–face intersection
  const tWL = clamp((waterY - crestY) / damH, 0, 1);
  const faceAtWL = crestL - tWL * upRun;
  const wlLabelX = Math.max(waterLeft + 4, faceAtWL - 52);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Dam cross-section">
      <defs>
        <linearGradient id="damFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#9a9a9a" />
          <stop offset="50%" stopColor="#7a7a7a" />
          <stop offset="100%" stopColor="#5e5e5e" />
        </linearGradient>
        <linearGradient id="wFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#8ec4dc" stopOpacity="0.92" />
          <stop offset="100%" stopColor="#4a8aa8" stopOpacity="0.97" />
        </linearGradient>
        <pattern id="coreHatch" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="5" stroke="#2c3e50" strokeWidth="1.2" />
        </pattern>
        <pattern id="coreHatch2" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(-45)">
          <line x1="0" y1="0" x2="0" y2="5" stroke="#34495e" strokeWidth="0.8" opacity="0.65" />
        </pattern>
      </defs>

      <rect width={W} height={H} fill="#fafafa" />
      <rect x={0} y={bed} width={W} height={H - bed} fill="#2a2a2a" />
      <line x1={0} y1={bed} x2={W} y2={bed} stroke="#111" strokeWidth="1.3" />

      {/* Dam body — solid */}
      <polygon
        points={`${toeL},${bed} ${crestL},${crestY} ${crestR},${crestY} ${toeR},${bed}`}
        fill="url(#damFill)"
        stroke="#1a1a1a"
        strokeWidth="1.15"
      />

      {/* Zoned core — hashed + internal labels */}
      {showCore && (
        <g>
          <polygon
            points={`${coreBotL},${bed} ${coreTopL},${coreTopY} ${coreTopR},${coreTopY} ${coreBotR},${bed}`}
            fill="#c8d4dc"
            stroke="#1a1a1a"
            strokeWidth="0.85"
          />
          <polygon
            points={`${coreBotL},${bed} ${coreTopL},${coreTopY} ${coreTopR},${coreTopY} ${coreBotR},${bed}`}
            fill="url(#coreHatch)"
            opacity="0.5"
          />
          <polygon
            points={`${coreBotL},${bed} ${coreTopL},${coreTopY} ${coreTopR},${coreTopY} ${coreBotR},${bed}`}
            fill="url(#coreHatch2)"
            opacity="0.35"
          />
          {/* ct at top of core */}
          <line x1={coreTopL} y1={coreTopY + 10} x2={coreTopR} y2={coreTopY + 10} stroke="#1a1a1a" strokeWidth="0.6" />
          <line x1={coreTopL} y1={coreTopY + 7} x2={coreTopL} y2={coreTopY + 13} stroke="#1a1a1a" strokeWidth="0.6" />
          <line x1={coreTopR} y1={coreTopY + 7} x2={coreTopR} y2={coreTopY + 13} stroke="#1a1a1a" strokeWidth="0.6" />
          <text x={cx} y={coreTopY + 20} textAnchor="middle" fontSize="7.5" fontFamily="Georgia, serif" fill="#1a1a1a">
            {`ct = ${fmt(ctM, 1)} m`}
          </text>
          {/* Zc on core face */}
          <text
            x={(coreTopR + coreBotR) / 2 + 4}
            y={(coreTopY + bed) / 2}
            fontSize="7.5"
            fontFamily="Georgia, serif"
            fill="#1a1a1a"
          >
            {`Zc = ${fmt(Zc, 1)}`}
          </text>
          {/* cb at base inside/near core */}
          <line x1={coreBotL} y1={bed - 14} x2={coreBotR} y2={bed - 14} stroke="#1a1a1a" strokeWidth="0.6" />
          <line x1={coreBotL} y1={bed - 17} x2={coreBotL} y2={bed - 11} stroke="#1a1a1a" strokeWidth="0.6" />
          <line x1={coreBotR} y1={bed - 17} x2={coreBotR} y2={bed - 11} stroke="#1a1a1a" strokeWidth="0.6" />
          <text x={cx} y={bed - 18} textAnchor="middle" fontSize="7.5" fontFamily="Georgia, serif" fill="#1a1a1a">
            {`cb = ${fmt(cbM, 1)} m`}
          </text>
        </g>
      )}

      {/* Open breach cut only after growth */}
      {hasOpenBreach && (
        <polygon
          points={`${cx - WbPx / 2},${zbY} ${cx + WbPx / 2},${zbY} ${cx + WbPx / 2 + (bed - zbY) * 0.18},${bed} ${cx - WbPx / 2 - (bed - zbY) * 0.18},${bed}`}
          fill="#f5f5f5"
          stroke="#1a1a1a"
          strokeWidth="0.9"
        />
      )}

      {/* Water — upstream pool only, never covers the dam body */}
      {WL > inputs.baseElev && (
        <polygon points={waterPts} fill="url(#wFill)" stroke="#2a6a85" strokeWidth="0.65" />
      )}

      {/* Thin overtopping sheet — crest band + slope-aligned spill ribbon only */}
      {sheetPts && <polygon points={sheetPts} fill="url(#wFill)" stroke="#2a6a85" strokeWidth="0.5" opacity="0.9" />}
      {spillPts && <polygon points={spillPts} fill="url(#wFill)" stroke="#2a6a85" strokeWidth="0.5" opacity="0.9" />}
      <line
        x1={waterLeft}
        y1={waterY}
        x2={hasOpenBreach && waterY < zbY + 4 ? cx - WbPx / 2 : faceAtWL}
        y2={waterY}
        stroke="#1a5270"
        strokeWidth="1"
        strokeDasharray="4 2.5"
      />

      {inHeadcut && xH > 0.02 && xH < C - 0.02 && (
        <g>
          <line
            x1={headcutX}
            y1={crestY}
            x2={headcutX}
            y2={Math.min(zbY + 16, bed - 14)}
            stroke="#c0392b"
            strokeWidth="1.3"
            strokeDasharray="3 2"
          />
          <text x={headcutX + 4} y={crestY + 11} fontSize="7.5" fontFamily="Georgia, serif" fill="#c0392b">
            {`xh = ${fmt(xH, 2)} m`}
          </text>
        </g>
      )}

      {inPiping && (
        <g>
          <circle cx={cx} cy={pipeY} r={pipeR} fill="#5a9bb5" stroke="#1a1a1a" strokeWidth="0.85" />
          <text x={cx + pipeR + 5} y={pipeY + 3} fontSize="7.5" fontFamily="Georgia, serif" fill="#1a1a1a">
            {`R = ${fmt(Rval, 2)} m`}
          </text>
        </g>
      )}

      <line x1={crestL} y1={crestY} x2={crestR} y2={crestY} stroke="#111" strokeWidth="1.7" />

      {/* Crest width */}
      <DimH x1={crestL} x2={crestR} y={crestY - 11} label={`C = ${fmt(C, 1)} m`} />

      {/* Face slopes */}
      <text x={toeL + upRun * 0.22} y={bed - 8} fontSize="7.5" fontFamily="Georgia, serif" fill="#1a1a1a">
        {`Z₁ = ${fmt(inputs.zUp, 1)}`}
      </text>
      <text x={crestR + dnRun * 0.22} y={bed - 8} fontSize="7.5" fontFamily="Georgia, serif" fill="#1a1a1a">
        {`Z₂ = ${fmt(inputs.zDown, 1)}`}
      </text>

      {/* Hb on the RIGHT */}
      <DimV x={toeR + 18} y1={crestY} y2={bed} label={`Hb = ${fmt(Hb, 1)} m`} />

      {/* Hc on the RIGHT (outside dam), zoned only */}
      {showCore && (
        <DimV x={toeR + 48} y1={coreTopY} y2={bed} label={`Hc = ${fmt(HcM, 1)} m`} />
      )}

      {hasOpenBreach && (
        <g>
          <line x1={cx - WbPx / 2} y1={zbY + 9} x2={cx + WbPx / 2} y2={zbY + 9} stroke="#1a1a1a" strokeWidth="0.65" />
          <text x={cx} y={zbY + 20} textAnchor="middle" fontSize="7.5" fontFamily="Georgia, serif" fill="#1a1a1a">
            {`Wb = ${fmt(Wb, 2)} m`}
          </text>
        </g>
      )}

      {/* WL near water–face intersection */}
      <text x={wlLabelX} y={waterY - 4} fontSize="7.5" fontFamily="Georgia, serif" fill="#1a5270">
        {`WL = ${fmt(WL, 2)} m`}
      </text>

      {/* overtopping far left — never on top of WL */}
      {freeboardVal <= 0.05 && (
        <text x={waterLeft} y={Math.min(waterY, crestY) - 10} fontSize="8" fontFamily="Georgia, serif" fill="#c0392b">
          overtopping
        </text>
      )}
      {freeboardVal > 0.05 && (
        <text x={waterLeft} y={(crestY + waterY) / 2 + 3} fontSize="7.5" fontFamily="Georgia, serif" fill="#1a1a1a">
          {`f = ${fmt(freeboardVal, 2)} m`}
        </text>
      )}

      {/* Stage badge */}
      <g transform={`translate(${W - 96}, 8)`}>
        <rect width={88} height={14} rx={3} fill="#2c2c2c" />
        <text x={44} y={10.5} textAnchor="middle" fontSize="8.5" fontFamily="system-ui, sans-serif" fill="#f5f5f5">
          {stageShort(stage, inputs.mode, hasOpenBreach)}
        </text>
      </g>
    </svg>
  );
}

function stageShort(stage: string, mode: string, hasOpen: boolean) {
  if (stage === "piping") return "Piping";
  if (stage === "headcut") return "Headcut";
  if (stage === "open" || hasOpen) return "Open breach";
  if (stage === "empty") return "Empty";
  return mode === "piping" ? "Piping" : "Overtopping";
}

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}

function DimH({ x1, x2, y, label }: { x1: number; x2: number; y: number; label: string }) {
  const mid = (x1 + x2) / 2;
  return (
    <g>
      <line x1={x1} y1={y} x2={x2} y2={y} stroke="#1a1a1a" strokeWidth="0.65" />
      <line x1={x1} y1={y - 2.8} x2={x1} y2={y + 2.8} stroke="#1a1a1a" strokeWidth="0.65" />
      <line x1={x2} y1={y - 2.8} x2={x2} y2={y + 2.8} stroke="#1a1a1a" strokeWidth="0.65" />
      <text x={mid} y={y - 4} textAnchor="middle" fontSize="7.5" fontFamily="Georgia, serif" fill="#1a1a1a">
        {label}
      </text>
    </g>
  );
}

function DimV({ x, y1, y2, label }: { x: number; y1: number; y2: number; label: string }) {
  return (
    <g>
      <line x1={x} y1={y1} x2={x} y2={y2} stroke="#1a1a1a" strokeWidth="0.65" />
      <line x1={x - 2.8} y1={y1} x2={x + 2.8} y2={y1} stroke="#1a1a1a" strokeWidth="0.65" />
      <line x1={x - 2.8} y1={y2} x2={x + 2.8} y2={y2} stroke="#1a1a1a" strokeWidth="0.65" />
      <text x={x + 5} y={(y1 + y2) / 2 + 3} fontSize="7.5" fontFamily="Georgia, serif" fill="#1a1a1a">
        {label}
      </text>
    </g>
  );
}
