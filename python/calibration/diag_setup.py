"""Setup diagnostics before the calibration grid (not calibration runs; nothing here is scored or fitted).

Checks whether the calibration cases erode at all with the cal-1 setup:
  1. WalshS3 (fine sand) at default factors, 600 s
  2. WalshS3 with the largest grid value of the transport factor (f_t = 10), 600 s
  3. WalshS3 at default factors on a 3x finer grid (about 4 cm cells, notch resolved), 600 s
  4. E1S1 (silty sand, jet-test kd) at default factors over the 2 h test window
  5. Castlewood (field, gravel) at default factors, 3 h
Usage: python -u calibration\\diag_setup.py      (about 30-60 min; writes ..\\runs\\diag_setup.json)
"""
import json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases as C

checks = [
    ("WalshS3 default", "WalshS3", {"f_t": 1.0}, None, None),
    ("WalshS3 f_t=10", "WalshS3", {"f_t": 10.0}, None, None),
    ("WalshS3 grid H/24", "WalshS3", {"f_t": 1.0}, None, 24.0),
    ("E1S1 default", "E1S1", {}, None, None),
    ("Castlewood default 3 h", "Castlewood", {}, 10800.0, None),
]
out = []
T0 = time.time()
for i, (name, cid, fac, t_end, grid) in enumerate(checks, 1):
    c = C.load_case(cid)
    mesh, res, mat, cfg, meta = C.build(c, fac, grid)
    print(f"\n=== check {i}/{len(checks)}: {name}  (grid {meta['nx']} x {meta['ny']}, cell {meta['dx']:.3f} m, "
          f"simulating {t_end or c['t_end']:.0f} s)   started at {time.strftime('%H:%M:%S')}", flush=True)
    chunk = 30.0 if c["kind"] == "lab" and (t_end or c["t_end"]) <= 1200 else 300.0
    r = C.run(c, fac, t_end=t_end, grid_divisor=grid, chunk_s=chunk, progress=True)
    r["check"] = name
    keep = {k: r[k] for k in ("check", "Qp", "Tp_h", "B", "breached", "max_lowering_m", "t_end_phys_s",
                              "t_switch_phys_s", "stop_reason", "steps", "wall_s", "grid", "balances")}
    keep["obs"] = c["obs"]
    out.append(keep)
    print(f"--> RESULT {name}: Qp={r['Qp']:.4g} (obs {c['obs'].get('Qp')})  Tp={r['Tp_h']*60:.1f} min  B={r['B']:.2f} m  "
          f"max lowering={r['max_lowering_m']:.3f} m  breached={r['breached']}  wall={r['wall_s']/60:.1f} min", flush=True)
p = HERE.parent.parent / "runs" / "diag_setup.json"
p.write_text(json.dumps(out, indent=1, default=str))
print(f"\nall checks done in {(time.time() - T0) / 60:.1f} min; written {p}")
