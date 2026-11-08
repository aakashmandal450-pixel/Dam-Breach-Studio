"""cal-2 runner smoke test: model options applied, early no-breach stop, Numba backend, checkpoint resume exact."""
import sys, json, shutil, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import fast_hydro
assert fast_hydro.enable()
import cases as C
ok = True
def check(name, cond, info=""):
    global ok
    ok &= bool(cond)
    print(f"{'PASS' if cond else 'FAIL'}  {name}  {info}", flush=True)

c = C.load_case("E1S1")
_, _, _, cfg, _ = C.build(c, None, model="cal-2")
opts = json.loads((HERE / "cal2_config.json").read_text())["engine_options"]
check("cal-2 engine options applied", all(getattr(cfg, k) == v or (v is None and getattr(cfg, k) is None) for k, v in opts.items()),
      str({k: getattr(cfg, k) for k in opts}))
_, _, _, cfg1, _ = C.build(c, None)
check("cal-1 build unchanged (defaults)", cfg1.headcut_mode == "cell" and cfg1.collapse_mode == "unsupported")

# early no-breach stop: very low erodibility, E1S1 observed Tp 0.666 h -> stop at 2.0 h
r = C.run(c, {"f_kd": 0.01, "C_h": 0.0316, "f_t": 1.0}, model="cal-2", early_no_breach_factor=3.0, post_peak_stop=True)
check("early no-breach stop", r["stop_cause"] == "no_breach_early" and not r["censored"] and abs(r["t_end_phys_s"] - 7192.8) < 700,
      f"stop {r['stop_cause']} at {r['t_end_phys_s']:.0f} s, breached {r['breached']}, cpu {r['cpu_s']:.0f} s")
sc = C.score(c, r)
check("early-stopped run is scored", "J" in sc, f"J = {sc.get('J')}")

# breaching run: not stopped early; checkpoint/resume reproduces the uninterrupted run exactly
fac = {"f_kd": 3.16, "C_h": 1.0, "f_t": 1.0}
ref = C.run(c, fac, model="cal-2", early_no_breach_factor=3.0, post_peak_stop=True)
check("breaching run not stopped early", ref["stop_cause"] != "no_breach_early" and ref["t_init_phys_s"] is not None,
      f"stop {ref['stop_cause']}, initiation {ref['t_init_phys_s']}, Qp {ref['Qp']:.4g}, B {ref['B']:.3g}, cpu {ref['cpu_s']:.0f} s")
tmp = Path(tempfile.mkdtemp())
part = C.run(c, fac, model="cal-2", early_no_breach_factor=3.0, post_peak_stop=True, max_cpu_seconds=0.4 * ref["cpu_s"],
             checkpoint_dir=str(tmp), checkpoint_every_cpu_s=0.1 * ref["cpu_s"])
res = C.run(c, fac, model="cal-2", early_no_breach_factor=3.0, post_peak_stop=True, checkpoint_dir=str(tmp),
            checkpoint_every_cpu_s=0.1 * ref["cpu_s"])
same = all(res[k] == ref[k] for k in ("Qp", "Tp_h", "B", "breached", "steps", "max_lowering_m", "t_init_phys_s", "stop_cause"))
check("checkpoint resume identical to uninterrupted run", same and part["censored"] and res["restarts"] >= 1,
      f"first part stopped by {part['stop_cause']}; resumed restarts {res['restarts']}; Qp {res['Qp']:.6g} vs {ref['Qp']:.6g}")
shutil.rmtree(tmp, ignore_errors=True)
check("balances", max(abs(x) for x in ref["balances"]) < 1e-6, str(ref["balances"]))
print("cal-2 smoke: " + ("ALL PASS" if ok else "FAILED"))
sys.exit(0 if ok else 1)
