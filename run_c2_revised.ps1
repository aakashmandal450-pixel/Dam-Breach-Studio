# C2 verification, revision 2 (user decisions 2026-11-28): V5r, V5br, V7br, V12r and the runtime benchmark.
# Steady states are converged first (with C2 at CFL 0.9) and cached; then all jobs run in parallel.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_c2_revised.ps1
#         powershell -ExecutionPolicy Bypass -File .\run_c2_revised.ps1 -Only V7br,V12r
param([string]$Only = "V5r,V5br,V7br,V12r,COST")
$Repo  = "D:\My Projects\Dam-Breach-Studio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log   = Join-Path ([Environment]::GetFolderPath("Desktop")) "onedim_c2_revised_$Stamp.log"
Set-Location (Join-Path $Repo "python")
python -B -u -m onedim.verification.c2_tests_r2 --only $Only 2>&1 | Tee-Object -FilePath $Log
Write-Host "`nLog written to $Log"
