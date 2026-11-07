# Engine profiling: short runs of the calibration cases, timing + cProfile (read-only; grid not touched).
# One process, about 20-30 min. The log goes to the Desktop; raw profiles to runs\profile\.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_profile.ps1"
Set-Location $PSScriptRoot
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "profile_engine_$(Get-Date -Format yyyyMMdd_HHmm).txt"
python -u calibration\profile_engine.py 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log
"`nLog: $log"
