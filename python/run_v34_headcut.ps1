# V3.4 headcut check: (1) the V3.4 unit tests with NumPy and Numba (the engine gained an optional headcut log),
# (2) the headcut rule alone on one scarp at five cell sizes (calibration\v34_headcut_check.py, about a minute),
# (3) Laurel Run at H/9 and H/12 with F1-F6 and the headcut log (variant wedge_f6_hc; 2 new runs, about 20 min).
# Live progress in this window; full log and the summaries on the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_v34_headcut.ps1"
param([int]$Workers = 5)
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
$desk = [Environment]::GetFolderPath("Desktop")
$log = Join-Path $desk "v34_headcut_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"V3.4 headcut check  $(Get-Date -Format s)   python: $(python --version 2>&1)   git: $(git -C (Split-Path $root -Parent) log --oneline -1 2>&1)" | Tee-Object -FilePath $log
foreach ($backend in @("NumPy", "Numba")) {
    "`n===== tests\v3_4_tests.py ($backend) =====" | Tee-Object -FilePath $log -Append
    if ($backend -eq "NumPy") { python -u tests\v3_4_tests.py 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append }
    else { python -u tests\run_with_fast.py tests\v3_4_tests.py 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append }
    if ($LASTEXITCODE -ne 0) { "TESTS FAILED ($backend) - the diagnostic run was not started. Log: $log" | Tee-Object -FilePath $log -Append; exit 1 }
}
"`n===== headcut rule alone (calibration\v34_headcut_check.py) =====" | Tee-Object -FilePath $log -Append
python -u calibration\v34_headcut_check.py --desktop $desk 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
"`n===== diagnostic run with the headcut log (calibration\v34_diag_laurel.py) =====" | Tee-Object -FilePath $log -Append
$sw = [Diagnostics.Stopwatch]::StartNew()
python -u calibration\v34_diag_laurel.py --workers $Workers --desktop $desk 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
$code = $LASTEXITCODE; $sw.Stop()
("finished in {0:N1} min, exit code {1}" -f $sw.Elapsed.TotalMinutes, $code) | Tee-Object -FilePath $log -Append
$(if ($code -eq 0) { "ALL DONE" } else { "FAILED - run again to retry" }) | Tee-Object -FilePath $log -Append
"Log: $log   Summaries: Desktop\v34_headcut_check_*.txt, Desktop\v34_diag_laurel_summary_*.txt   Runs: ..\runs\v34_diag_laurel\" | Tee-Object -FilePath $log -Append
exit $code
