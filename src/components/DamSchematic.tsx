import type { SimStep, StudioInputs } from "@/lib/breach/types";

interface Props {
  inputs: StudioInputs;
  step: SimStep | null;
}

export function DamSchematic({ inputs, step }: Props) {
  const Hb = Math.max(inputs.crestElev - inputs.baseElev, 0.1);
  const W = 720;
  const H = 340;
  const ground = 300;
  const crestY = 70;
  const damH = ground - crestY;
  const crestW = 70;
  const upRun = inputs.zUp * damH * 0.35;
  const dnRun = inputs.zDown * damH * 0.35;
  const cx = 400;
  const crestL = cx - crestW / 2;
  const crestR = cx + crestW / 2;
  const toeL = crestL - upRun;
  const toeR = crestR + dnRun;

  const elevToY = (elev: number) => {
    const t = (inputs.crestElev - elev) / Hb;
    return crestY + t * damH;
  };

  const WL = step?.WL ?? inputs.initialWL;
  const waterY = elevToY(WL);
  const zbY = elevToY(step?.zb ?? (inputs.mode === "piping" ? inputs.pipeInvert : inputs.crestElev));
  const WbPx = Math.min(180, Math.max(8, ((step?.Wb ?? inputs.initialNotchWidth) / Math.max(inputs.crestLength, 1)) * 220));
  const pipeR = Math.max(4, ((step?.R ?? inputs.initialPipeRadius) / Hb) * damH * 2.2);
  const pipeY = elevToY(inputs.pipeInvert);
  const stage = step?.stage ?? (inputs.mode === "overtopping" ? "open" : "piping");
  const open = stage === "open" || stage === "empty" || stage === "headcut" || inputs.mode === "overtopping";
  const inHeadcut = stage === "headcut";

  // Headcut position: 0 at downstream crest edge → crestWidth at upstream edge
  const C = Math.max(inputs.crestWidth, 0.5);
  const xH = clamp(step?.xHeadcut ?? 0, 0, C);
  const headcutX = crestR - (xH / C) * crestW;

  const waterPoly = `${toeL - 160},${ground} ${toeL - 160},${Math.min(waterY, ground)} ${
    open && waterY < zbY + 2
      ? `${cx - WbPx / 2},${Math.min(waterY, zbY)} ${cx + WbPx / 2},${Math.min(waterY, zbY)}`
      : `${crestL},${Math.min(waterY, ground)}`
  } ${toeL},${ground}`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Dam cross-section schematic">
      <rect width={W} height={H} fill="#f2eee6" />
      <line x1="24" y1={ground} x2="696" y2={ground} stroke="#1a1814" strokeWidth="1.2" />

      <polygon
        points={`${toeL},${ground} ${crestL},${crestY} ${crestR},${crestY} ${toeR},${ground}`}
        fill="#c4b49a"
        stroke="#1a1814"
        strokeWidth="1.4"
      />

      {open && (
        <polygon
          points={`${cx - WbPx / 2},${zbY} ${cx + WbPx / 2},${zbY} ${cx + WbPx / 2 + (ground - zbY) * 0.25},${ground} ${
            cx - WbPx / 2 - (ground - zbY) * 0.25
          },${ground}`}
          fill="#f2eee6"
          stroke="#245460"
          strokeWidth="1.2"
        />
      )}

      {inHeadcut && xH > 0 && xH < C && (
        <g>
          <line
            x1={headcutX}
            y1={crestY}
            x2={headcutX}
            y2={Math.min(zbY + 24, ground - 20)}
            stroke="#b45309"
            strokeWidth="2.2"
            strokeDasharray="4 2"
          />
          <text
            x={headcutX + 6}
            y={crestY + 16}
            fontSize="10"
            fontFamily="IBM Plex Sans"
            fill="#b45309"
          >
            x_h = {xH.toFixed(2)} m
          </text>
        </g>
      )}

      {WL > inputs.baseElev && (
        <polygon points={waterPoly} fill="#3d6f82" fillOpacity="0.35" stroke="#245460" strokeWidth="1" />
      )}

      {!open && (
        <circle cx={cx} cy={pipeY} r={pipeR} fill="#3d6f82" fillOpacity="0.55" stroke="#245460" strokeWidth="1.2" />
      )}

      <polyline points={`${crestL},${crestY} ${crestR},${crestY}`} stroke="#1a1814" strokeWidth="2.2" />

      <Dim x1={crestL} x2={crestR} y={crestY - 18} label={`C = ${inputs.crestWidth} m`} />
      <Dim v x1={24} y1={crestY} y2={ground} label={`Hb = ${Hb.toFixed(1)} m`} />
      <text x={toeL + 8} y={ground - 10} className="fill-foreground" fontSize="10" fontFamily="IBM Plex Sans">
        Z1 = {inputs.zUp} H:1V
      </text>
      <text x={crestR + 12} y={ground - 10} className="fill-foreground" fontSize="10" fontFamily="IBM Plex Sans">
        Z2 = {inputs.zDown} H:1V
      </text>
      {open && (
        <text x={cx} y={zbY - 8} textAnchor="middle" fontSize="10" fontFamily="IBM Plex Sans" fill="#245460">
          Wb = {(step?.Wb ?? inputs.initialNotchWidth).toFixed(2)} m
        </text>
      )}
      {!open && (
        <text x={cx + pipeR + 10} y={pipeY + 4} fontSize="10" fontFamily="IBM Plex Sans" fill="#245460">
          R = {(step?.R ?? inputs.initialPipeRadius).toFixed(3)} m
        </text>
      )}
      <text x={40} y={Math.min(waterY, ground) - 8} fontSize="10" fontFamily="IBM Plex Sans" fill="#245460">
        WL = {WL.toFixed(2)} m
      </text>
    </svg>
  );
}

function clamp(v: number, lo: number, hi: number) {
  return Math.min(hi, Math.max(lo, v));
}

function Dim({
  x1,
  x2,
  y,
  y1,
  y2,
  label,
  v,
}: {
  x1?: number;
  x2?: number;
  y?: number;
  y1?: number;
  y2?: number;
  label: string;
  v?: boolean;
}) {
  if (v && x1 != null && y1 != null && y2 != null) {
    return (
      <g>
        <line x1={x1} y1={y1} x2={x1} y2={y2} stroke="#6b6560" strokeWidth="0.8" />
        <text x={x1 + 6} y={(y1 + y2) / 2} fontSize="10" fontFamily="IBM Plex Sans" fill="#6b6560">
          {label}
        </text>
      </g>
    );
  }
  if (x1 == null || x2 == null || y == null) return null;
  return (
    <g>
      <line x1={x1} y1={y} x2={x2} y2={y} stroke="#6b6560" strokeWidth="0.8" />
      <text x={(x1 + x2) / 2} y={y - 4} textAnchor="middle" fontSize="10" fontFamily="IBM Plex Sans" fill="#6b6560">
        {label}
      </text>
    </g>
  );
}
