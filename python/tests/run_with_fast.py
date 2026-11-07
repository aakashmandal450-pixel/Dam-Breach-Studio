"""Run one engine test script with the Numba backend switched on (fast_hydro.enable()).

Usage:  python tests\\run_with_fast.py tests\\v3_engine_regression.py
"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import fast_hydro  # noqa: E402

if not fast_hydro.enable():
    print("FAIL  numba not installed (python -m pip install numba)")
    sys.exit(2)
print("[fast_hydro] Numba backend enabled for this test run", flush=True)
script = Path(sys.argv[1]).resolve()
sys.argv = [str(script)] + sys.argv[2:]
runpy.run_path(str(script), run_name="__main__")
