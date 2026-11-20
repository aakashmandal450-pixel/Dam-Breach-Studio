"""V3.4 architecture report: what the engine actually does, and where the physics can go wrong.

No simulation. This reads the engine by introspection (so it stays true as the code changes) and
builds each case's initial mesh, then reports:

  1. MORPH STEP ORDER     the sequence of rules inside Morphology.step, with what each reads and
                          writes, and the sequencing hazards that order creates
  2. CONFIG TABLE         all EngineConfig fields: engine default -> cal-2 value -> F1-F7 value,
                          marking every field a fix changes
  3. LAW AXES             every interchangeable formula, its allowed values, which one is active,
                          and which alternatives exist but are unused
  4. GEOMETRY vs GATES    for each case and grid, the real discretized face slopes of the initial
                          bed measured both per-cell and cumulatively, next to the headcut gate
                          thresholds they must clear. This is where a gate that cannot fire shows
                          up as a number rather than a guess.
  5. RED FLAGS            automated consistency checks across 1-4

Usage (from the python folder):
    python -u calibration\\v34_architecture_report.py
    python -u calibration\\v34_architecture_report.py --desktop <folder>
    python -u calibration\\v34_architecture_report.py --cases LaurelRun --grids 9 12
"""
from __future__ import annotations

import argparse
import dataclasses
import enum
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import breach_engine_2d_v3_2 as E  # noqa: E402
import cases as C  # noqa: E402

NEUTRAL = {"f_kd": 1.0, "C_h": 1.0, "f_t": 1.0}

# The fix ladder, exactly as the isolation/grid-check scripts define it.
FIXES = {
    "F1 hydrostatic_reconstruction": {"hydrostatic_reconstruction": "chen_noelle"},
    "F2 headcut_overfall":           {"headcut_overfall": "free"},
    "F3 adaptation_dx_floor":        {"adaptation_dx_floor": False},
    "F4 collapse_to_repose":         {"collapse_to_repose": True},
    "F5 collapse_mode":              {"collapse_mode": "bank_wedge"},
    "F6 sediment_face_flux":         {"sediment_face_flux": "hydro"},
    "F7 headcut_face_slope":         {"headcut_face_slope": 1.0},
}
FULL = {k: v for d in FIXES.values() for k, v in d.items()}

# Morphology.step, read from the source. Each entry: rule, gate, the config that picks the law,
# what it writes, and the diag key it reports volume under.
STEP_ORDER = [
    ("1 transport / Exner", "always", "transport, suspended_load, erosion_shear, sediment_face_flux",
     "mesh.z_b, mesh.S", "transport_net_erosion_m3"),
    ("2 lateral erosion", "cfg.lateral_erosion_enabled", "lateral_model, lateral_noncohesive, lateral_directions",
     "mesh.z_b, mesh.S", "lateral_m3"),
    ("3 headcut migrate", "cfg.headcut_enabled", "headcut_mode, headcut_face_slope, headcut_method, headcut_overfall",
     "mesh.z_b, mesh.S", "headcut_m3"),
    ("4 bank collapse", "cfg.bank_collapse_enabled", "collapse_mode, collapse_to_repose, bank_stability",
     "mesh.z_b, mesh.S", "collapsed_m3"),
    ("5 toe scour", "col > 0 and cfg.toe_scour_factor > 0", "toe_scour_factor",
     "mesh.z_b, mesh.S", "toe_scour_m3"),
    ("6 dry-cell settling", "always", "h_dry",
     "mesh.z_b += S/(1-p) where dry; S = 0 where dry", "(not reported)"),
]

SEQUENCING_NOTES = [
    "The headcut (3) runs AFTER transport (1). Transport smooths the bed every step, so the headcut",
    "    sees a profile that has already been relaxed before it looks for a steep face.",
    "The headcut (3) runs BEFORE collapse (4). Anything the headcut steepens within a step can be",
    "    flattened again by collapse in the same step, before the next headcut call ever sees it.",
    "Both (3) and (4) write mesh.z_b with no shared face definition: they can act on the same cells",
    "    in one step from different geometric readings of it.",
    "Dry-cell settling (6) dumps all suspended sediment in dry cells straight onto the bed. On a",
    "    fine grid more cells fall dry per step, so this path is cell-size sensitive by construction.",
]

# Law axes: field -> (allowed values, where it is validated)
LAW_AXES = {
    "transport": ([e.value for e in E.TransportFormula], "TransportFormula enum"),
    "suspended_load": (["none", "wu2000"], "line ~945"),
    "erosion_shear": (["total", "grain"], "line ~2057"),
    "threshold_D": (["D50", "geometric", "D90"], "line ~987"),
    "sediment_face_flux": (["centred", "hydro"], "line ~1871  (F6)"),
    "headcut_method": (["energy", "temple", "sites"], "line ~1448"),
    "headcut_mode": (["cell", "scarp"], "line ~1790"),
    "headcut_overfall": (["any", "free"], "line ~1781  (F2)"),
    "collapse_mode": (["unsupported", "all_pairs", "bank_wedge"], "line ~1195  (F5)"),
    "bank_stability": ([e.value for e in E.BankStabilityMethod], "criticalDepth only; others raise"),
    "lateral_model": (["critical_shear"], "single implementation"),
    "lateral_noncohesive": (["excess_shear", "off"], "line ~1057"),
    "lateral_directions": (["y", "xy"], "line ~1059"),
    "hydrostatic_reconstruction": (["audusse", "chen_noelle"], "line ~749  (F1)"),
    "friction_model": (["chezy", "manning"], "line ~883"),
    "adaptation_length_mode": (["fixed"], "single implementation"),
}

SUBSYSTEM = [
    ("hydraulics", ("hydrostatic", "friction", "manning", "spatial_order", "cfl", "damping",
                    "h_dry", "eps", "kinematic")),
    ("transport / Exner", ("transport", "suspended", "erosion_shear", "threshold_D", "sediment_face",
                           "adaptation", "chen", "detachment", "theta")),
    ("headcut", ("headcut",)),
    ("bank collapse", ("collapse", "bank_", "toe_scour")),
    ("lateral", ("lateral",)),
    ("limits / numerics", ("morph", "dt_", "max_dz", "z_floor", "print_every", "snapshot",
                           "checkpoint", "bed_shear", "channelization")),
]


def _fmt(v):
    if isinstance(v, enum.Enum):
        return repr(v.value)
    if isinstance(v, float) and v not in (0.0, 1.0) and (abs(v) < 1e-3 or abs(v) >= 1e5):
        return f"{v:.3e}"
    return repr(v)


def cfg_value(cfg, name):
    return getattr(cfg, name, "<absent>")


def section_1(out):
    out("=" * 100)
    out("1. MORPH STEP ORDER   (breach_engine_2d_v3_2.py, Morphology.step)")
    out("=" * 100)
    out("Every morphological update runs these in this fixed order, on the same mesh, within one dt:")
    out("")
    out(f"  {'rule':22s} {'runs when':38s} {'volume reported as':26s}")
    out(f"  {'-' * 22} {'-' * 38} {'-' * 26}")
    for name, gate, laws, writes, diag in STEP_ORDER:
        out(f"  {name:22s} {gate:38s} {diag:26s}")
        out(f"  {'':22s}   law picked by: {laws}")
        out(f"  {'':22s}   writes: {writes}")
    out("")
    out("SEQUENCING HAZARDS created by this order:")
    for n in SEQUENCING_NOTES:
        out(f"  - {n}" if not n.startswith("    ") else f"    {n.strip()}")
    out("")


def section_2(out):
    out("=" * 100)
    out("2. CONFIG TABLE   engine default -> cal-2 -> F1-F7")
    out("=" * 100)
    base = E.EngineConfig()
    # cal-2 values come from a real build so the model layer is applied exactly as a run would
    case = C.load_case("LaurelRun")
    _, _, _, cal2, _ = C.build(case, dict(NEUTRAL), grid_divisor=9.0, model="cal-2")
    _, _, _, full, _ = C.build(case, dict(NEUTRAL), grid_divisor=9.0, model="cal-2", overrides=dict(FULL))
    fields = {f.name: f for f in dataclasses.fields(E.EngineConfig)}
    which_fix = {k: n for n, d in FIXES.items() for k in d}
    shown = set()
    for label, keys in SUBSYSTEM:
        rows = []
        for name in fields:
            if name in shown or not any(k in name for k in keys):
                continue
            d, c2, fl = _fmt(getattr(base, name, None)), _fmt(cfg_value(cal2, name)), _fmt(cfg_value(full, name))
            if d == c2 == fl:
                continue                                  # unchanged everywhere: not interesting here
            shown.add(name)
            tag = ""
            if c2 != d:
                tag = "cal-2"
            if fl != c2:
                tag = which_fix.get(name, "override")
            rows.append((name, d, c2, fl, tag))
        if not rows:
            continue
        out(f"--- {label} " + "-" * (96 - len(label)))
        out(f"  {'field':30s} {'default':>16s} {'cal-2':>16s} {'F1-F7':>16s}  changed by")
        for name, d, c2, fl, tag in sorted(rows):
            out(f"  {name:30s} {d:>16s} {c2:>16s} {fl:>16s}  {tag}")
        out("")
    rest = [n for n in fields if n not in shown]
    out(f"({len(shown)} fields differ between default / cal-2 / F1-F7; "
        f"{len(rest)} identical in all three and omitted.)")
    out("")


def section_3(out):
    out("=" * 100)
    out("3. LAW AXES   which formula is active, and what else is implemented")
    out("=" * 100)
    case = C.load_case("LaurelRun")
    _, _, _, cal2, _ = C.build(case, dict(NEUTRAL), grid_divisor=9.0, model="cal-2")
    _, _, _, full, _ = C.build(case, dict(NEUTRAL), grid_divisor=9.0, model="cal-2", overrides=dict(FULL))
    out(f"  {'field':30s} {'cal-2':>14s} {'F1-F7':>14s}   unused alternatives")
    out(f"  {'-' * 30} {'-' * 14} {'-' * 14}   {'-' * 30}")
    for name, (allowed, _where) in LAW_AXES.items():
        c2, fl = cfg_value(cal2, name), cfg_value(full, name)
        c2s = c2.value if isinstance(c2, enum.Enum) else c2
        fls = fl.value if isinstance(fl, enum.Enum) else fl
        unused = [a for a in allowed if a != fls]
        out(f"  {name:30s} {str(c2s):>14s} {str(fls):>14s}   {', '.join(unused) if unused else '(none)'}")
    out("")
    out("  The 'unused alternatives' column is the formula-vs-architecture test set: hold the")
    out("  architecture fixed and swap these. If the pathology survives every formula, the fault is")
    out("  in how the rules are composed, not in any one law. v34_law_sweep.py runs exactly that.")
    out("")


def face_slopes(z_line, ds, tol=1e-9):
    """Per-cell and best cumulative downhill slope along one profile.

    For a uniformly sloping face every window has the same slope, so among windows that reach the
    maximum (within tol) we report the LONGEST one - that makes span/H describe the whole face
    rather than whichever single cell happened to be found first.
    """
    z = np.asarray(z_line, dtype=float)
    d = z[:-1] - z[1:]
    per_cell = float(np.max(d / ds)) if d.size else 0.0
    n = z.size
    best_cum = 0.0
    for a in range(n - 1):
        for b in range(a + 1, n):
            drop = z[a] - z[b]
            if drop > 0:
                sl = drop / ((b - a) * ds)
                if sl > best_cum:
                    best_cum = sl
    best_span, best_H = 0, 0.0
    if best_cum > 0:
        for a in range(n - 1):
            for b in range(a + 1, n):
                drop = z[a] - z[b]
                if drop <= 0:
                    continue
                sl = drop / ((b - a) * ds)
                if sl >= best_cum - tol and (b - a) > best_span:
                    best_span, best_H = b - a, drop
    return per_cell, best_cum, best_span, best_H


def section_4(out, case_ids, grids):
    out("=" * 100)
    out("4. GEOMETRY vs GATES   measured on each case's INITIAL bed, down the breach axis")
    out("=" * 100)
    out("  A scarp must clear BOTH of these to be acted on:")
    out("    headcut_mode='scarp'  (C1, _migrate_scarp)        : scarp's OVERALL slope >= headcut_min_slope")
    out("    headcut_face_slope set (F7, _migrate_scarp_volume): EACH CELL's slope >= headcut_face_slope")
    out("")
    rows = []
    for cid in case_ids:
        case = C.load_case(cid)
        for gd in grids:
            mesh, _res, mat, cal2, _meta = C.build(case, dict(NEUTRAL), grid_divisor=float(gd), model="cal-2")
            _m2, _r2, _mt2, full, _mm2 = C.build(case, dict(NEUTRAL), grid_divisor=float(gd),
                                                 model="cal-2", overrides=dict(FULL))
            z0 = mesh.z_b
            ic = int(np.argmax(z0.max(axis=1)))            # crest row
            jc = int(np.argmin(z0[ic]))                    # breach axis column (pilot notch)
            pc, cum, span, Hwin = face_slopes(z0[:, jc], mesh.dx)
            rows.append(dict(case=cid, gd=gd, nx=z0.shape[0], ny=z0.shape[1], dx=mesh.dx,
                             zu=case["zu"], zd=case["zd"], per_cell=pc, cum=cum, span=span, H=Hwin,
                             min_slope=cal2.headcut_min_slope, face_slope=full.headcut_face_slope,
                             seg=cal2.headcut_seg_slope, phi=mat.phi, coh=mat.cohesion))
    out(f"  {'case':11s} {'grid':5s} {'nx x ny':10s} {'dx[m]':7s} {'1/zu':6s} {'1/zd':6s} "
        f"{'maxcell':8s} {'maxcum':7s} {'span':5s} {'H[m]':6s} {'C1 gate':8s} {'F7 gate':8s}")
    out("  " + "-" * 96)
    for r in rows:
        out(f"  {r['case']:11s} H/{r['gd']:<4d} {r['nx']:4d} x{r['ny']:4d} {r['dx']:7.3f} "
            f"{1 / r['zu']:6.3f} {1 / r['zd']:6.3f} {r['per_cell']:8.3f} {r['cum']:7.3f} "
            f"{r['span']:5d} {r['H']:6.2f} {r['min_slope']:8.2f} {r['face_slope']:8.2f}")
    out("")
    out("  1/zu, 1/zd are the as-built upstream and downstream face slopes (rise over run).")
    out("  maxcell / maxcum are measured from the discretized initial bed: the steepest single cell")
    out("  drop, and the steepest slope over any contiguous window (span cells, height H).")
    out("")
    return rows


def section_5(out, rows):
    out("=" * 100)
    out("5. RED FLAGS")
    out("=" * 100)
    flags = []
    by_case_grids = {}
    for r in rows:
        by_case_grids.setdefault(r["case"], []).append(r)

    for cid, rs in by_case_grids.items():
        rs = sorted(rs, key=lambda r: r["gd"])
        gl = ", ".join(f"H/{r['gd']}" for r in rs)
        fs = rs[0]["face_slope"]
        pcs = [r["per_cell"] for r in rs]
        cums = [r["cum"] for r in rs]

        if fs is not None and all(pp < fs for pp in pcs):
            flags.append(
                f"{cid} ({gl}): F7 gate CANNOT FIRE on the initial bed at any of these grids. "
                f"Steepest single-cell slope is {min(pcs):.3f}-{max(pcs):.3f}, the gate needs "
                f"{fs:.2f}. _migrate_scarp_volume tests EACH CELL, so no scarp is detected until "
                f"erosion builds a single cell steeper than {fs:.2f}.")
        elif fs is not None and any(abs(pp - fs) < 1e-6 for pp in pcs):
            flags.append(
                f"{cid} ({gl}): F7 gate sits EXACTLY ON the as-built face slope "
                f"({max(pcs):.3f} vs gate {fs:.2f}). Whether it fires is then decided by "
                f"floating-point round-off, so the behaviour is erratic rather than physical - "
                f"expect the peak to jump between grids for no physical reason.")

        if all(cc >= rs[0]["min_slope"] > 0 for cc in cums):
            flags.append(
                f"{cid} ({gl}): C1 gate DOES fire on the initial bed (cumulative slope "
                f"{min(cums):.3f}-{max(cums):.3f} >= headcut_min_slope {rs[0]['min_slope']:.2f}), over "
                f"a window up to {max(r['span'] for r in rs)} cells / {max(r['H'] for r in rs):.2f} m. "
                f"That window is the as-built dam face, not a headcut - the rule erodes the whole "
                f"face at the headcut rate.")

        if fs is not None and all(cc < fs for cc in cums):
            flags.append(
                f"{cid} ({gl}): even measured CUMULATIVELY the bed only reaches "
                f"{min(cums):.3f}-{max(cums):.3f}, below the F7 gate of {fs:.2f}. Reformulating the "
                f"gate from per-cell to cumulative will NOT make it fire at this threshold - the "
                f"threshold has to come down to the face slope, or a steep face must be created "
                f"physically first.")
    # grid sensitivity of the per-cell measure
    by_case = {}
    for r in rows:
        by_case.setdefault(r["case"], []).append(r)
    for cid, rs in by_case.items():
        rs = sorted(rs, key=lambda r: r["gd"])
        if len(rs) > 1:
            pcs = [r["per_cell"] for r in rs]
            cums = [r["cum"] for r in rs]
            if max(pcs) > 0 and (max(pcs) - min(pcs)) / max(pcs) > 0.05:
                flags.append(
                    f"{cid}: the PER-CELL slope of the same physical face changes with grid "
                    f"({', '.join(f'H/{r_[0]}={r_[1]:.3f}' for r_ in [(r['gd'], r['per_cell']) for r in rs])}). "
                    f"A per-cell gate is therefore grid dependent by construction.")
            if max(cums) > 0 and (max(cums) - min(cums)) / max(cums) <= 0.05:
                flags.append(
                    f"{cid}: the CUMULATIVE slope is grid independent "
                    f"({', '.join(f'H/{r_[0]}={r_[1]:.3f}' for r_ in [(r['gd'], r['cum']) for r in rs])}) "
                    f"- the right quantity to gate on, whatever threshold is chosen.")
    flags.append("Morphology.step runs headcut between transport and collapse (section 1). Transport "
                 "smooths the face before the headcut reads it; collapse can flatten it after. Any "
                 "steep face the headcut needs must survive both within one dt.")
    if not flags:
        out("  none")
    for i, f in enumerate(flags, 1):
        out(f"  [{i}] {f}")
        out("")
    out("")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", nargs="+", default=["LaurelRun", "Castlewood"])
    ap.add_argument("--grids", nargs="+", type=int, default=[6, 9, 12])
    ap.add_argument("--desktop", default=None)
    a = ap.parse_args()

    lines = []

    def out(s=""):
        lines.append(s)
        print(s, flush=True)

    out(f"V3.4 ARCHITECTURE REPORT    {time.strftime('%Y-%m-%d %H:%M')}")
    out(f"engine: breach_engine_2d_v3_2.py    cases: {', '.join(a.cases)}    grids: "
        f"{', '.join('H/' + str(g) for g in a.grids)}")
    out("")
    section_1(out)
    section_2(out)
    section_3(out)
    rows = section_4(out, a.cases, a.grids)
    section_5(out, rows)

    if a.desktop:
        p = Path(a.desktop, f"v34_architecture_report_{time.strftime('%Y%m%d_%H%M')}.txt")
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nWritten: {p}", flush=True)


if __name__ == "__main__":
    main()
