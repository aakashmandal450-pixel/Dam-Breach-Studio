# V3.4 isolation test: Castlewood, F1+F2+F3, neutral factors, H/9 and H/12, four variants
# (base / collapse to repose / headcut off / both) = 8 runs, about 20-40 min with 5 workers.
# Live progress in this window; full log and the results summary on the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_v34_isolation.ps1"
param([int]$Workers = 5)
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
$desk = [Environment]::GetFolderPath("Desktop")
$log = Join-Path $desk "v34_isolation_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"V3.4 isolation test  $(Get-Date -Format s)   python: $(python --version 2>&1)   git: $(git -C (Split-Path $root -Parent) log --oneline -1 2>&1)" | Tee-Object -FilePath $log
$sw = [Diagnostics.Stopwatch]::StartNew()
python -u calibration\v34_isolation.py --workers $Workers --desktop $desk 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
$code = $LASTEXITCODE; $sw.Stop()
("finished in {0:N1} min, exit code {1}" -f $sw.Elapsed.TotalMinutes, $code) | Tee-Object -FilePath $log -Append
$(if ($code -eq 0) { "ALL DONE" } else { "FAILED - run again to retry" }) | Tee-Object -FilePath $log -Append
"Log: $log   Summary: Desktop\v34_isolation_summary_*.txt   Runs: ..\runs\v34_isolation\" | Tee-Object -FilePath $log -Append
exit $code
