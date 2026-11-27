# B12d mechanism checks M1-M4 (interface flux response, no-section-change conduits, term trace, B12a
# contractions at two CFL values). Prints each job as it finishes; log to the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_b12d_mechanism.ps1
$Repo  = "D:\My Projects\Dam-Breach-Studio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log   = Join-Path ([Environment]::GetFolderPath("Desktop")) "onedim_b12d_mechanism_$Stamp.log"
Set-Location (Join-Path $Repo "python")
python -B -u -m onedim.verification.b12d_mechanism 2>&1 | Tee-Object -FilePath $Log
Write-Host "`nLog written to $Log"
