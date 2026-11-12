# V3.4 F6 check: (1) all test suites with NumPy and Numba (run_v33_tests.ps1, a few minutes),
# (2) the Laurel Run diagnostic with F6 (H/9 and H/12, three bank variants; 6 new runs, about 25 min),
# (3) the grid check with F6 (Laurel Run + Castlewood at H/6, H/9, H/12; pair rule and whole-bank rule; 12 new runs,
#     about 35 min). Finished runs are skipped. Total about one hour with 5 workers.
# Live progress in this window; full log and the two summaries on the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_v34_f6.ps1"
param([int]$Workers = 5)
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
$desk = [Environment]::GetFolderPath("Desktop")
$log = Join-Path $desk "v34_f6_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"V3.4 F6 check  $(Get-Date -Format s)   python: $(python --version 2>&1)   git: $(git -C (Split-Path $root -Parent) log --oneline -1 2>&1)" | Tee-Object -FilePath $log

"`n===== all test suites (run_v33_tests.ps1) =====" | Tee-Object -FilePath $log -Append
powershell -ExecutionPolicy Bypass -File (Join-Path $root "run_v33_tests.ps1") 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) {
    "TESTS FAILED - the dam runs were not started. Log: $log" | Tee-Object -FilePath $log -Append
    exit 1
}
$overall = 0
"`n===== diagnostic run with F6 (calibration\v34_diag_laurel.py) =====" | Tee-Object -FilePath $log -Append
$sw = [Diagnostics.Stopwatch]::StartNew()
python -u calibration\v34_diag_laurel.py --workers $Workers --desktop $desk 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { $overall = 1 }
("diagnostic run finished in {0:N1} min" -f $sw.Elapsed.TotalMinutes) | Tee-Object -FilePath $log -Append

"`n===== grid-convergence check, setups F12346 and F123456 (calibration\v34_grid_check.py) =====" | Tee-Object -FilePath $log -Append
$sw = [Diagnostics.Stopwatch]::StartNew()
python -u calibration\v34_grid_check.py --workers $Workers --desktop $desk 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { $overall = 1 }
("grid check finished in {0:N1} min" -f $sw.Elapsed.TotalMinutes) | Tee-Object -FilePath $log -Append
$(if ($overall -eq 0) { "ALL DONE (tests passed)" } else { "SOMETHING FAILED - see above; run again to retry" }) | Tee-Object -FilePath $log -Append
"Log: $log   Summaries: Desktop\v34_diag_laurel_summary_*.txt, Desktop\v34_gridcheck_summary_*.txt" | Tee-Object -FilePath $log -Append
exit $overall
