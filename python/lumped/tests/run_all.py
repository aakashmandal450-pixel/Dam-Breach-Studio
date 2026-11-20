"""Run every lumped-model test (tests/test_*.py) and print one PASS/FAIL line per test.

Usage (from the python folder):  python -m lumped.tests.run_all
Exit code 0 when everything passes, 1 otherwise.
"""
import sys
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = HERE.parent.parent                      # the python/ folder
sys.path.insert(0, str(PY))


class _Live(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self._t0 = time.time()

    def _line(self, test, status):
        self.stream.writeln(f"  {status:4s}  {test.id():70s} {time.time() - self._t0:6.2f} s")
        self.stream.flush()

    def addSuccess(self, test):
        unittest.TestResult.addSuccess(self, test); self._line(test, "PASS")

    def addFailure(self, test, err):
        unittest.TestResult.addFailure(self, test, err); self._line(test, "FAIL")

    def addError(self, test, err):
        unittest.TestResult.addError(self, test, err); self._line(test, "ERR")

    def addSkip(self, test, reason):
        unittest.TestResult.addSkip(self, test, reason); self._line(test, "SKIP")


def main() -> int:
    import lumped
    print(f"Lumped 1-D model tests  (package {lumped.__version__})", flush=True)
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_*.py", top_level_dir=str(PY))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=0, resultclass=_Live)
    res = runner.run(suite)
    for kind, items in (("FAILURE", res.failures), ("ERROR", res.errors)):
        for test, tb in items:
            print(f"\n--- {kind}: {test.id()}\n{tb}")
    ok = res.wasSuccessful()
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}  ({res.testsRun} tests, {len(res.failures)} failures, "
          f"{len(res.errors)} errors, {len(res.skipped)} skipped)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
