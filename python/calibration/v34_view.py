"""V3.4 run viewer: watch a 2-D breach run and see which rule is (or is not) doing the work.

Reads the .npz recordings written by calibration/v34_diag_laurel.py (and v34_record.py) plus the
matching __headcut.json gate log, and opens an interactive window with a time slider.

Panels
  1 PLAN VIEW        bed change z(t) - z0 over the whole mesh, with the wet area outlined, the crest
                     line and breach axis marked. A breach that never widens is obvious here.
  2 LONG PROFILE     bed down the breach axis, earlier times ghosted behind the current one, so you
                     see whether a steep face ever forms or the profile just sags.
  3 SLOPE vs GATES   per-cell slope down that same profile, with the C1 and F7 gate thresholds drawn
                     as lines. If the trace never crosses a line, that gate can never fire - this is
                     the panel that shows a dead rule rather than letting you infer it.
  4 CROSS-SECTION    bed along the crest line with the initial crest overlaid: breach width.
  5 HYDROGRAPH       outflow and lake level.
  6 WORK BY RULE     cumulative volume moved by transport / headcut / lateral / collapse. Whichever
                     curve is flat is a rule that is not participating.

Controls: drag the slider, or use left/right arrows to step and space to play/pause.

Usage (from the python folder):
    python -u calibration\\v34_view.py --list
    python -u calibration\\v34_view.py --run LaurelRun__H12__wedge_f6_hc
    python -u calibration\\v34_view.py --run LaurelRun__H9__wedge_f6_hc --compare LaurelRun__H12__wedge_f6_hc
    python -u calibration\\v34_view.py --run LaurelRun__H12__wedge_f6_hc --save
    python -u calibration\\v34_view.py --run LaurelRun__H12__wedge_f6_hc --save --gif
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUN_DIRS = [ROOT / "runs" / d for d in ("v34_diag_laurel", "v34_record", "v34_gridcheck_f7",
                                        "v34_isolation_f567", "v34_isolation", "v34_isolation_laurel")]

RULES = ("transport_net_erosion_m3", "headcut_m3", "lateral_m3", "collapsed_m3")
RULE_LABEL = ("transport / Exner", "headcut", "lateral", "collapse")
RULE_COLOR = ("#1f77b4", "#d62728", "#2ca02c", "#9467bd")


def find_runs():
    out = []
    for d in RUN_DIRS:
        if d.is_dir():
            out += sorted(d.glob("*.npz"))
    return out


def resolve(name: str) -> Path:
    p = Path(name)
    if p.is_file():
        return p
    for cand in find_runs():
        if cand.stem == name or cand.name == name:
            return cand
    raise SystemExit(f"run not found: {name}\nUse --list to see what is available.")


class Run:
    def __init__(self, path: Path, c1_gate: float, f7_gate: float):
        self.path = path
        self.stem = path.stem
        d = np.load(path)
        self.d = d
        self.t = np.asarray(d["t"], dtype=float)
        self.Q = np.asarray(d["Q"], dtype=float)
        self.WL = np.asarray(d["WL"], dtype=float)
        self.long_z = np.asarray(d["long_z"], dtype=float)      # (nt, nx) breach axis
        self.long_h = np.asarray(d["long_h"], dtype=float)
        self.xsec_z = np.asarray(d["xsec_z"], dtype=float)      # (nt, ny) crest line
        self.xsec_h = np.asarray(d["xsec_h"], dtype=float)
        self.cum = np.asarray(d["cum"], dtype=float)            # (nt, 4) by RULES
        self.z0 = np.asarray(d["z0"], dtype=float)
        self.z_end = np.asarray(d["z_end"], dtype=float)
        self.h_end = np.asarray(d["h_end"], dtype=float)
        self.dx = float(d["dx"]); self.dy = float(d["dy"])
        self.ic = int(d["ic"]); self.jc = int(d["jc"])
        self.nt = len(self.t)
        self.c1_gate, self.f7_gate = c1_gate, f7_gate
        self.x = (np.arange(self.long_z.shape[1]) + 0.5) * self.dx
        self.y = (np.arange(self.xsec_z.shape[1]) + 0.5) * self.dy
        self.z0_long = self.z0[:, self.jc]
        self.z0_xsec = self.z0[self.ic]
        # full 2-D field series, when the recorder saved them
        self.field_t = np.asarray(d["field_t"], dtype=float) if "field_t" in d.files else None
        self.field_z = np.asarray(d["field_z"], dtype=float) if "field_z" in d.files else None
        self.field_h = np.asarray(d["field_h"], dtype=float) if "field_h" in d.files else None
        # gate log, if recorded alongside
        self.hc = []
        hp = path.with_name(path.stem + "__headcut.json")
        if hp.exists():
            try:
                self.hc = json.loads(hp.read_text())
            except Exception:
                self.hc = []

    def field_at(self, t_now: float):
        """Nearest stored 2-D (z, h) to t_now, or None when the run has no field series."""
        if self.field_t is None or self.field_z is None or len(self.field_t) == 0:
            return None
        i = int(np.argmin(np.abs(self.field_t - t_now)))
        h = self.field_h[i] if self.field_h is not None else None
        return self.field_z[i], h, float(self.field_t[i])

    # --- derived diagnostics -------------------------------------------------
    def slope_profile(self, k: int):
        """Per-cell downhill slope along the breach axis at frame k."""
        z = self.long_z[k]
        return (z[:-1] - z[1:]) / self.dx

    def best_cumulative(self, k: int):
        """Steepest slope over any contiguous downhill window, and its span/height."""
        z = self.long_z[k]
        n = z.size
        best, span, H = 0.0, 0, 0.0
        for a in range(n - 1):
            za = z[a]
            for b in range(a + 1, n):
                drop = za - z[b]
                if drop > 0:
                    s = drop / ((b - a) * self.dx)
                    if s > best:
                        best, span, H = s, b - a, drop
        return best, span, H

    def width_at(self, k: int, frac: float = 0.5):
        """Breach width on the crest line: cells lowered by >= frac of the deepest lowering."""
        low = np.maximum(self.z0_xsec - self.xsec_z[k], 0.0)
        mx = float(low.max())
        if mx <= 0.05:
            return 0.0, mx
        return float(np.count_nonzero(low >= frac * mx) * self.dy), mx

    def gate_reasons(self, t_now: float, window: float = 60.0):
        """Why the headcut was inactive near t_now, from the recorded gate log."""
        if not self.hc:
            return None
        near = [e for e in self.hc if abs(e["t"] - t_now) <= window and e.get("sign", 1) > 0]
        if not near:
            return {"n": 0}
        keys = ("slope", "wet_foot", "q", "free")
        return {"n": len(near),
                "active": sum(1 for e in near if e.get("active")),
                **{k: sum(1 for e in near if not e.get("ok_" + k, True)) for k in keys},
                "max_slope": max((e.get("slope", 0.0) for e in near), default=0.0)}


def build_figure(runs, k0=0):
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider

    nrun = len(runs)
    fig = plt.figure(figsize=(16.5, 9.6 if nrun == 1 else 10.4))
    fig.canvas.manager.set_window_title("V3.4 run viewer - " + " | ".join(r.stem for r in runs))
    gs = fig.add_gridspec(3, 3, hspace=0.42, wspace=0.26,
                          left=0.06, right=0.985, top=0.93, bottom=0.11)

    ax_plan = fig.add_subplot(gs[0, 0])
    ax_long = fig.add_subplot(gs[0, 1])
    ax_slope = fig.add_subplot(gs[0, 2])
    ax_xsec = fig.add_subplot(gs[1, 0])
    ax_hyd = fig.add_subplot(gs[1, 1])
    ax_work = fig.add_subplot(gs[1, 2])
    ax_txt = fig.add_subplot(gs[2, :])
    ax_txt.axis("off")

    state = {"k": k0, "playing": False}
    ref = runs[0]
    nt_max = max(r.nt for r in runs)

    def frame_for(r, k):
        """Match frames by model time so compared runs stay in step."""
        if r is ref:
            return min(k, r.nt - 1)
        return int(np.clip(np.searchsorted(r.t, ref.t[min(k, ref.nt - 1)]), 0, r.nt - 1))

    def draw(_=None):
        k = state["k"]
        for ax in (ax_plan, ax_long, ax_slope, ax_xsec, ax_hyd, ax_work):
            ax.clear()

        # --- 1 plan view: bed change (first run only; it is a 2-D field) ----
        kk = frame_for(ref, k)
        fld = ref.field_at(ref.t[kk])
        wet_mask = None
        if fld is not None:
            zf, hf, tf = fld
            chg = zf - ref.z0
            wet_mask = hf if hf is not None else None
            title = f"1 PLAN VIEW  bed change  (field at t={tf:.0f}s)"
        elif kk == ref.nt - 1:
            chg = ref.z_end - ref.z0
            wet_mask = ref.h_end
            title = "1 PLAN VIEW  bed change (final field)"
        else:
            chg = np.full_like(ref.z0, np.nan)
            chg[:, ref.jc] = ref.long_z[kk] - ref.z0_long
            chg[ref.ic, :] = ref.xsec_z[kk] - ref.z0_xsec
            title = "1 PLAN VIEW  recorded lines only (re-record with v34_record.py for fields)"
        vmax = max(1e-6, float(np.nanmax(np.abs(chg))))
        im = ax_plan.imshow(chg.T, origin="lower", aspect="auto", cmap="RdBu_r",
                            vmin=-vmax, vmax=vmax,
                            extent=[0, ref.z0.shape[0] * ref.dx, 0, ref.z0.shape[1] * ref.dy])
        if wet_mask is not None:
            try:
                ax_plan.contour(
                    np.linspace(0, ref.z0.shape[0] * ref.dx, ref.z0.shape[0]),
                    np.linspace(0, ref.z0.shape[1] * ref.dy, ref.z0.shape[1]),
                    (np.asarray(wet_mask) > 1e-3).T.astype(float),
                    levels=[0.5], colors="#0b6fa4", linewidths=0.9)
            except Exception:
                pass
        ax_plan.axvline((ref.ic + 0.5) * ref.dx, color="k", lw=0.8, ls="--")
        ax_plan.axhline((ref.jc + 0.5) * ref.dy, color="g", lw=0.8, ls="--")
        ax_plan.set_title(title, fontsize=9)
        ax_plan.set_xlabel("x  (down valley) [m]", fontsize=8)
        ax_plan.set_ylabel("y  (across) [m]", fontsize=8)
        if not hasattr(draw, "_cb"):
            draw._cb = fig.colorbar(im, ax=ax_plan, fraction=0.046)
            draw._cb.set_label("z - z0 [m]", fontsize=8)

        # --- 2 longitudinal profile ----------------------------------------
        for r, ls in zip(runs, ("-", "--")):
            kr = frame_for(r, k)
            for g in range(max(0, kr - 40), kr, 8):          # ghosts
                ax_long.plot(r.x, r.long_z[g], color="0.82", lw=0.6, zorder=1)
            ax_long.plot(r.x, r.z0_long, color="0.35", lw=0.9, ls=":", zorder=2,
                         label=f"{r.stem.split('__')[1]} initial" if r is ref else None)
            ax_long.plot(r.x, r.long_z[kr], lw=1.7, ls=ls, zorder=4,
                         label=f"{r.stem.split('__')[1]}  t={r.t[kr]:.0f}s")
            wet = r.long_h[kr] > 1e-3
            ax_long.fill_between(r.x, r.long_z[kr], r.long_z[kr] + r.long_h[kr],
                                 where=wet, color="#4da6ff", alpha=0.30, zorder=3)
        ax_long.set_title("2 LONG PROFILE  down the breach axis", fontsize=9)
        ax_long.set_xlabel("x [m]", fontsize=8); ax_long.set_ylabel("z [m]", fontsize=8)
        ax_long.legend(fontsize=7, loc="upper right")

        # --- 3 slope vs gates ----------------------------------------------
        for r, ls in zip(runs, ("-", "--")):
            kr = frame_for(r, k)
            sl = r.slope_profile(kr)
            ax_slope.plot(r.x[:-1], sl, lw=1.3, ls=ls,
                          label=f"{r.stem.split('__')[1]} per-cell")
        ax_slope.axhline(ref.c1_gate, color="#ff7f0e", lw=1.5,
                         label=f"C1 gate  {ref.c1_gate:g}  (cumulative)")
        ax_slope.axhline(ref.f7_gate, color="#d62728", lw=1.5,
                         label=f"F7 gate  {ref.f7_gate:g}  (per-cell)")
        ax_slope.axhline(0, color="0.7", lw=0.6)
        ax_slope.set_title("3 SLOPE vs GATES  (the money panel)", fontsize=9)
        ax_slope.set_xlabel("x [m]", fontsize=8)
        ax_slope.set_ylabel("downhill slope [-]", fontsize=8)
        top = max(ref.f7_gate * 1.35, ref.c1_gate * 1.6,
                  float(np.nanmax([np.nanmax(r.slope_profile(frame_for(r, k))) for r in runs])) * 1.2)
        ax_slope.set_ylim(-0.1, max(0.6, top))
        ax_slope.legend(fontsize=7, loc="upper right")

        # --- 4 cross-section / width ---------------------------------------
        for r, ls in zip(runs, ("-", "--")):
            kr = frame_for(r, k)
            ax_xsec.plot(r.y, r.z0_xsec, color="0.35", lw=0.9, ls=":")
            ax_xsec.plot(r.y, r.xsec_z[kr], lw=1.6, ls=ls,
                         label=f"{r.stem.split('__')[1]}")
            wet = r.xsec_h[kr] > 1e-3
            ax_xsec.fill_between(r.y, r.xsec_z[kr], r.xsec_z[kr] + r.xsec_h[kr],
                                 where=wet, color="#4da6ff", alpha=0.30)
        w, mx = ref.width_at(frame_for(ref, k))
        ax_xsec.set_title(f"4 CROSS-SECTION  crest line - width {w:.1f} m, deepest cut {mx:.2f} m",
                          fontsize=9)
        ax_xsec.set_xlabel("y [m]", fontsize=8); ax_xsec.set_ylabel("z [m]", fontsize=8)
        ax_xsec.legend(fontsize=7, loc="upper right")

        # --- 5 hydrograph ---------------------------------------------------
        for r, ls in zip(runs, ("-", "--")):
            kr = frame_for(r, k)
            ax_hyd.plot(r.t, r.Q, lw=1.3, ls=ls, color="#1f77b4",
                        label=f"Q {r.stem.split('__')[1]}")
            ax_hyd.plot(r.t[kr], r.Q[kr], "o", ms=5, color="#1f77b4")
        ax_hyd.axvline(ref.t[frame_for(ref, k)], color="0.6", lw=0.8)
        ax_hyd.set_title("5 HYDROGRAPH  outflow", fontsize=9)
        ax_hyd.set_xlabel("t [s]", fontsize=8); ax_hyd.set_ylabel("Q [m3/s]", fontsize=8)
        ax_hyd.legend(fontsize=7, loc="upper left")
        axw = ax_hyd.twinx()
        axw.plot(ref.t, ref.WL, lw=1.0, color="0.5", ls="-.")
        axw.set_ylabel("lake level [m]", fontsize=8, color="0.4")
        axw.tick_params(labelsize=7, colors="0.4")

        # --- 6 work by rule --------------------------------------------------
        kr = frame_for(ref, k)
        for i, (lab, col) in enumerate(zip(RULE_LABEL, RULE_COLOR)):
            ax_work.plot(ref.t, ref.cum[:, i], lw=1.4, color=col, label=lab)
            ax_work.plot(ref.t[kr], ref.cum[kr, i], "o", ms=4, color=col)
        ax_work.axvline(ref.t[kr], color="0.6", lw=0.8)
        ax_work.set_title("6 WORK BY RULE  cumulative volume moved", fontsize=9)
        ax_work.set_xlabel("t [s]", fontsize=8); ax_work.set_ylabel("volume [m3]", fontsize=8)
        ax_work.legend(fontsize=7, loc="upper left")

        # --- readout ---------------------------------------------------------
        lines = []
        for r in runs:
            kr = frame_for(r, k)
            cum_s, span, Hs = r.best_cumulative(kr)
            sl = r.slope_profile(kr)
            pc = float(np.nanmax(sl)) if sl.size else 0.0
            w_, mx_ = r.width_at(kr)
            vols = ", ".join(f"{lab.split(' /')[0]} {r.cum[kr, i]:,.0f}"
                             for i, lab in enumerate(RULE_LABEL))
            lines.append(
                f"{r.stem}   t={r.t[kr]:7.1f}s   Q={r.Q[kr]:8.1f} m3/s   width={w_:6.1f} m   "
                f"deepest cut={mx_:5.2f} m")
            lines.append(
                f"      steepest per-cell slope {pc:6.3f}  vs F7 gate {r.f7_gate:g}"
                f"  ->  {'FIRES' if pc >= r.f7_gate else 'CANNOT FIRE'}        "
                f"steepest cumulative {cum_s:6.3f} over {span} cells / {Hs:5.2f} m"
                f"  vs C1 gate {r.c1_gate:g}  ->  {'FIRES' if cum_s >= r.c1_gate else 'CANNOT FIRE'}")
            lines.append(f"      volumes moved [m3]: {vols}")
            g = r.gate_reasons(r.t[kr])
            if g and g.get("n"):
                lines.append(
                    f"      gate log near this time: {g['n']} scarps, {g['active']} active; "
                    f"rejected for slope {g['slope']}, dry foot {g['wet_foot']}, no flow {g['q']}, "
                    f"drowned {g['free']}; max logged slope {g['max_slope']:.3f}")
            elif r.hc:
                lines.append("      gate log near this time: no scarps logged")
            lines.append("")
        ax_txt.text(0.0, 1.0, "\n".join(lines), family="monospace", fontsize=8.2,
                    va="top", ha="left", transform=ax_txt.transAxes)
        fig.canvas.draw_idle()

    ax_sl = fig.add_axes([0.08, 0.035, 0.84, 0.022])
    slider = Slider(ax_sl, "frame", 0, max(1, nt_max - 1), valinit=k0, valstep=1)

    def on_slide(v):
        state["k"] = int(v)
        draw()

    slider.on_changed(on_slide)

    def on_key(ev):
        if ev.key in ("right", "left"):
            state["k"] = int(np.clip(state["k"] + (1 if ev.key == "right" else -1), 0, nt_max - 1))
            slider.set_val(state["k"])
        elif ev.key in ("pageup", "pagedown"):
            d = 20 if ev.key == "pageup" else -20
            state["k"] = int(np.clip(state["k"] + d, 0, nt_max - 1))
            slider.set_val(state["k"])
        elif ev.key == " ":
            state["playing"] = not state["playing"]

    fig.canvas.mpl_connect("key_press_event", on_key)

    timer = fig.canvas.new_timer(interval=120)

    def tick():
        if state["playing"]:
            state["k"] = (state["k"] + 1) % nt_max
            slider.set_val(state["k"])

    timer.add_callback(tick)
    timer.start()

    draw()
    return fig, draw, state, slider, nt_max


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", help="npz path or stem, e.g. LaurelRun__H12__wedge_f6_hc")
    ap.add_argument("--compare", default=None, help="second run to overlay")
    ap.add_argument("--list", action="store_true", help="list available recordings")
    ap.add_argument("--frame", type=int, default=None, help="start frame (default: last)")
    ap.add_argument("--c1-gate", type=float, default=0.5, help="headcut_min_slope (C1 cumulative gate)")
    ap.add_argument("--f7-gate", type=float, default=1.0, help="headcut_face_slope (F7 per-cell gate)")
    ap.add_argument("--save", action="store_true", help="save a PNG instead of opening a window")
    ap.add_argument("--gif", action="store_true", help="with --save, also write an animated gif")
    ap.add_argument("--out", default=None, help="output folder for --save (default: alongside the npz)")
    a = ap.parse_args()

    found = find_runs()
    if a.list or not a.run:
        if not found:
            print("No .npz recordings found under:")
            for d in RUN_DIRS:
                print(f"  {d}")
            print("\nRun calibration/v34_diag_laurel.py or v34_record.py first.")
            return
        print(f"{len(found)} recordings:\n")
        for p in found:
            try:
                d = np.load(p)
                n, t1 = len(d["t"]), float(d["t"][-1])
                extra = "  +gate log" if p.with_name(p.stem + '__headcut.json').exists() else ""
                print(f"  {p.stem:44s} {n:5d} frames  t_end {t1:8.0f}s  "
                      f"{d['z0'].shape[0]:4d}x{d['z0'].shape[1]:<4d}{extra}")
            except Exception as e:
                print(f"  {p.stem:44s} (unreadable: {e})")
        print(f"\nViewer:  python -u calibration/v34_view.py --run {found[-1].stem}")
        return

    import matplotlib
    if a.save:
        matplotlib.use("Agg")
    runs = [Run(resolve(a.run), a.c1_gate, a.f7_gate)]
    if a.compare:
        runs.append(Run(resolve(a.compare), a.c1_gate, a.f7_gate))

    k0 = (runs[0].nt - 1) if a.frame is None else int(np.clip(a.frame, 0, runs[0].nt - 1))
    fig, draw, state, slider, nt_max = build_figure(runs, k0)

    if not a.save:
        import matplotlib.pyplot as plt
        print(f"frames: {nt_max}   arrows step, page up/down jump 20, space plays")
        plt.show()
        return

    outdir = Path(a.out) if a.out else runs[0].path.parent
    outdir.mkdir(parents=True, exist_ok=True)
    stem = runs[0].stem + ("__vs__" + runs[1].stem.split("__")[1] if len(runs) > 1 else "")
    png = outdir / f"view_{stem}_f{k0}.png"
    fig.savefig(png, dpi=130)
    print(f"written: {png}")

    if a.gif:
        from matplotlib.animation import FuncAnimation, PillowWriter
        step = max(1, nt_max // 60)
        frames = list(range(0, nt_max, step))

        def upd(k):
            state["k"] = k
            draw()
            return []

        anim = FuncAnimation(fig, upd, frames=frames, blit=False)
        gif = outdir / f"view_{stem}.gif"
        anim.save(gif, writer=PillowWriter(fps=6))
        print(f"written: {gif}  ({len(frames)} frames)")


if __name__ == "__main__":
    main()
