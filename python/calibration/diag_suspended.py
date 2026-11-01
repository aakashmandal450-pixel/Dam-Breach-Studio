"""Does adding suspended load (Wu, Wang & Jia 2000) make the sand cases erode? Diagnostics only, nothing is fitted.
Usage: python -u calibration\\diag_suspended.py     (about 10-20 min; writes ..\\runs\\diag_suspended.json)
"""
import json, sys, time
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cases as C

checks = [
    ("WalshS3 bed load only", "WalshS3", {}, {"suspended_load": "none"}, 600.0),
    ("WalshS3 + suspended", "WalshS3", {}, {"suspended_load": "wu2000"}, 600.0),
    ("WalshS3 + suspended, f_t=10", "WalshS3", {"f_t": 10.0}, {"suspended_load": "wu2000"}, 600.0),
    ("Castlewood bed load only 1 h", "Castlewood", {}, {"suspended_load": "none"}, 3600.0),
    ("Castlewood + suspended 1 h", "Castlewood", {}, {"suspended_load": "wu2000"}, 3600.0),
]
out, T0 = [], time.time()
for i, (name, cid, fac, ov, t_end) in enumerate(checks, 1):
    c = C.load_case(cid)
    print(f"\n=== check {i}/{len(checks)}: {name}  (simulating {t_end:.0f} s)  started {time.strftime('%H:%M:%S')}", flush=True)
    r = C.run(c, fac, t_end=t_end, chunk_s=(60.0 if t_end <= 1200 else 300.0), progress=True, overrides=ov)
    keep = {k: r[k] for k in ("Qp", "Tp_h", "B", "breached", "max_lowering_m", "wall_s", "balances")}
    keep.update(check=name, obs=c["obs"])
    out.append(keep)
    print(f"--> RESULT {name}: Qp={r['Qp']:.4g} m3/s (obs {c['obs'].get('Qp')})  max lowering={r['max_lowering_m']:.3f} m  "
          f"breached={r['breached']}  wall={r['wall_s']/60:.1f} min", flush=True)
p = HERE.parent.parent / "runs" / "diag_suspended.json"
p.write_text(json.dumps(out, indent=1, default=str))
print(f"\nall done in {(time.time()-T0)/60:.1f} min; written {p}")
