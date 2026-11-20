# Lumped 1-D model: time-step convergence (dt, dt/2, dt/4) on the calibration cases.
#   powershell -ExecutionPolicy Bypass -File ".\run_lumped_dt_convergence.ps1"
$ErrorActionPreference = "Stop"
$Repo    = "D:\My Projects\Dam-Breach-Studio"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$Log     = Join-Path $Desktop "lumped_dt_convergence_$Stamp.log"
Set-Location (Join-Path $Repo "python")
Write-Host "Lumped model - time-step convergence. Log: $Log" -ForegroundColor Cyan
& python -B -u -m lumped.verification.dt_convergence --desktop $Desktop 2>&1 | Tee-Object -FilePath $Log
exit $LASTEXITCODE
