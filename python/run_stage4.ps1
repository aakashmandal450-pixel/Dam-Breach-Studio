# Stage 4 runs (validation/calibration/STAGE4_PROTOCOL.md): blind cases on the frozen cal-2 model + LOO envelope +
# IMPACT_1-02 inflow sensitivity + Walsh S1/S3/S5 (seen) at H/16 and H/24. Never opens observed_validation.csv.
# A line per finished run; log to Desktop\stage4_runs_<time>.txt. Ctrl+C is safe: running again skips finished runs
# and resumes checkpoints. Keep the laptop plugged in, "Best performance", sleep off.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_stage4.ps1"
param([int]$Workers = 5)
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "stage4_runs_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"stage 4 runs  $(Get-Date -Format s)   python: $(python --version 2>&1)   workers: $Workers" | Tee-Object -FilePath $log
"git: $(git -C (Split-Path $root -Parent) log --oneline -1 2>&1)   tag: $(git -C (Split-Path $root -Parent) describe --tags 2>&1)" | Tee-Object -FilePath $log -Append
$sw = [Diagnostics.Stopwatch]::StartNew()
python -u calibration\run_stage4.py --workers $Workers 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
$code = $LASTEXITCODE; $sw.Stop()
("finished in {0:N1} h, exit code {1}" -f $sw.Elapsed.TotalHours, $code) | Tee-Object -FilePath $log -Append
$(if ($code -eq 0) { "ALL RUNS DONE - MANIFEST.json written (do NOT run score_stage4.py until 2C-02 is in and the runs are tagged)" } else { "NOT COMPLETE - run again to resume / retry" }) | Tee-Object -FilePath $log -Append
"Log: $log" | Tee-Object -FilePath $log -Append
exit $code
