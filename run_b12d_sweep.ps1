# B12d stability sweep: critical CFL against B_conduit / B_free (widths 0.3-5 m, depths, discharges,
# reverse transition, uniform control). Prints each case as it finishes; log to the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_b12d_sweep.ps1
$Repo  = "D:\My Projects\Dam-Breach-Studio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log   = Join-Path ([Environment]::GetFolderPath("Desktop")) "onedim_b12d_sweep_$Stamp.log"
Set-Location (Join-Path $Repo "python")
python -B -u -m onedim.verification.b12d_sweep 2>&1 | Tee-Object -FilePath $Log
Write-Host "`nLog written to $Log"
