# B12d conduit-outlet diagnosis (D1-D4). Prints each run as it finishes; log to the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_b12d_diagnosis.ps1              (t_max = 10000 s, the B12d spec)
#         powershell -ExecutionPolicy Bypass -File .\run_b12d_diagnosis.ps1 -TMax 2000   (shorter first look)
param([double]$TMax = 10000)
$Repo  = "D:\My Projects\Dam-Breach-Studio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log   = Join-Path ([Environment]::GetFolderPath("Desktop")) "onedim_b12d_diagnosis_$Stamp.log"
Set-Location (Join-Path $Repo "python")
python -B -u -m onedim.verification.b12d_diagnosis --tmax $TMax 2>&1 | Tee-Object -FilePath $Log
Write-Host "`nLog written to $Log"
