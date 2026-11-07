# V3.3 C5 check: Numba morphology kernels (fast_morph.py) against the NumPy engine.
#   Part 1: every kernel vs NumPy on 60 random beds (about 1 min, incl. first-time Numba compile)
#   Part 2: three full runs (E1S1, E2S2, Walsh S3; cal-1 factors, C1+C2 on), NumPy vs Numba morphology,
#           with CPU times (about 5 min)
# Writes a pass/fail log to the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_c5_check.ps1"
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "c5_check_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"V3.3 C5 check  $(Get-Date -Format s)   python: $(python --version 2>&1)" | Tee-Object -FilePath $log
$sw = [Diagnostics.Stopwatch]::StartNew()
python -u tests\c5_fast_morph_check.py --runs 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
$code = $LASTEXITCODE; $sw.Stop()
("Elapsed {0:N0} s" -f $sw.Elapsed.TotalSeconds) | Tee-Object -FilePath $log -Append
$(if ($code -eq 0) { "ALL PASS" } else { "FAILED (exit $code)" }) | Tee-Object -FilePath $log -Append
"Log: $log" | Tee-Object -FilePath $log -Append
exit $code
