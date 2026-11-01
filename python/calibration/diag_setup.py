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
for name, cid, fac, t_end, grid in checks:
    c = C.load_case(cid)
    t0 = time.time()
    r = C.run(c, fac, t_end=t_end, grid_divisor=grid)
    r["check"] = name
    keep = {k: r[k] for k in ("check", "Qp", "Tp_h", "B", "breached", "max_lowering_m", "t_end_phys_s",
                              "t_switch_phys_s", "stop_reason", "steps", "wall_s", "grid", "balances")}
    keep["obs"] = c["obs"]
    out.append(keep)
    print(f"{name:24s} Qp={r['Qp']:.4g} (obs {c['obs'].get('Qp')})  Tp={r['Tp_h']*60:.1f} min  B={r['B']:.2f} m  "
          f"max lowering={r['max_lowering_m']:.3f} m  breached={r['breached']}  wall={r['wall_s']/60:.1f} min", flush=True)
p = HERE.parent.parent / "runs" / "diag_setup.json"
p.write_text(json.dumps(out, indent=1, default=str))
print("written", p)
