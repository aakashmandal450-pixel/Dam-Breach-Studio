# V3.4 F3 check: (1) the V3.4 unit tests with NumPy and Numba, (2) the grid-convergence check of the fixes
# (Castlewood + Laurel Run, H/6, H/9, H/12, neutral factors; F1+F2 and F1+F2+F3; 12 runs, about 30-60 min).
# Live progress in this window; full log and a results summary on the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_v34_f3.ps1"
param([int]$Workers = 5)
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
$desk = [Environment]::GetFolderPath("Desktop")
$log = Join-Path $desk "v34_f3_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"V3.4 F3 check  $(Get-Date -Format s)   python: $(python --version 2>&1)" | Tee-Object -FilePath $log
$overall = 0
foreach ($backend in @("NumPy", "Numba")) {
    "`n===== tests\v3_4_tests.py ($backend) =====" | Tee-Object -FilePath $log -Append
    if ($backend -eq "NumPy") { python -u tests\v3_4_tests.py 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append }
    else { python -u tests\run_with_fast.py tests\v3_4_tests.py 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append }
    if ($LASTEXITCODE -ne 0) { $overall = 1; "TESTS FAILED ($backend)" | Tee-Object -FilePath $log -Append }
}
"`n===== grid-convergence check (calibration\v34_grid_check.py) =====" | Tee-Object -FilePath $log -Append
$sw = [Diagnostics.Stopwatch]::StartNew()
python -u calibration\v34_grid_check.py --workers $Workers --desktop $desk 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) { $overall = 1 }
("grid check finished in {0:N1} min" -f $sw.Elapsed.TotalMinutes) | Tee-Object -FilePath $log -Append
$(if ($overall -eq 0) { "ALL DONE (tests passed)" } else { "SOMETHING FAILED - see above" }) | Tee-Object -FilePath $log -Append
"Log: $log   Summary: Desktop\v34_gridcheck_summary_*.txt   Runs: ..\runs\v34_gridcheck\" | Tee-Object -FilePath $log -Append
exit $overall
