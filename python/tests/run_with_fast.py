"""Run v3_4_tests.py with the Numba fast_morph backend enabled.

Usage:  python tests/run_with_fast.py
  (from the python/ directory)
"""
import sys
from pathlib import Path

# Ensure the python/ directory is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fast_morph as FM
FM.enable()
print(f"fast_morph enabled: {FM._ENABLED}")

# Now run the test suite
exec(open(str(Path(__file__).resolve().parent / "v3_4_tests.py")).read())
