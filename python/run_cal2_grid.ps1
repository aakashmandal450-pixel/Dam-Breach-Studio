# cal-2 calibration grid (CAL2_PROPOSAL.md + CAL2_AMENDMENT_1.md, cal2_config.json).
#   Step 1: runner smoke test on E1S1 (about 5-10 min). The grid starts only if it passes.
#   Step 2: the grid, 234 runs, Numba backend, 1 thread per worker, post-peak stop, 8 h CPU budget per run,
#           checkpoints every 30 min CPU, early no-breach stop. Live status every 60 s; a line per finished run.
# Results: ..\runs\calibration_grid_cal2\   Log: Desktop\cal2_grid_<time>.txt
# Stop with Ctrl+C at any time; running this script again skips finished runs and resumes the others from their
# checkpoints (the smoke test is skipped on a resume with -SkipSmoke).
# Usage (keep the laptop plugged in, power mode "Best performance", sleep off):
#   powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_cal2_grid.ps1"
#   powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_cal2_grid.ps1" -SkipSmoke
param([int]$Workers = 5, [switch]$SkipSmoke)
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "cal2_grid_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"cal-2 grid  $(Get-Date -Format s)   python: $(python --version 2>&1)   workers: $Workers" | Tee-Object -FilePath $log
$commit = (git -C (Split-Path $root -Parent) log --oneline -1 2>&1)
"git: $commit" | Tee-Object -FilePath $log -Append
if (-not $SkipSmoke) {
    "`n===== Step 1: runner smoke test (calibration\smoke_cal2.py) =====" | Tee-Object -FilePath $log -Append
    python -u calibration\smoke_cal2.py 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) { "SMOKE TEST FAILED - grid not started" | Tee-Object -FilePath $log -Append; exit 1 }
}
"`n===== Step 2: cal-2 grid =====" | Tee-Object -FilePath $log -Append
python -u calibration\run_grid.py --config cal2 --list 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
$sw = [Diagnostics.Stopwatch]::StartNew()
python -u calibration\run_grid.py --config cal2 --workers $Workers 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
$code = $LASTEXITCODE; $sw.Stop()
("grid finished in {0:N1} h, exit code {1}" -f $sw.Elapsed.TotalHours, $code) | Tee-Object -FilePath $log -Append
$n = (Get-ChildItem (Join-Path (Split-Path $root -Parent) "runs\calibration_grid_cal2") -Filter *.json).Count
"result files: $n of 234" | Tee-Object -FilePath $log -Append
$(if ($code -eq 0 -and $n -eq 234) { "GRID COMPLETE - next: python calibration\fit.py --config cal2" } else { "GRID NOT COMPLETE - run again with -SkipSmoke to resume" }) | Tee-Object -FilePath $log -Append
"Log: $log" | Tee-Object -FilePath $log -Append
exit $code
