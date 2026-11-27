# B12d conduit-outlet diagnosis (D1-D4). Prints each run as it finishes; log to the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_b12d_diagnosis.ps1              (t_max = 10000 s, the B12d spec)
#         powershell -ExecutionPolicy Bypass -File .\run_b12d_diagnosis.ps1 -TMax 2000   (shorter first look)
#         powershell -ExecutionPolicy Bypass -File .\run_b12d_diagnosis.ps1 -Configs D3 -Outlets submerged   (only those runs)
param([double]$TMax = 10000, [string]$Configs = "D3,D2,D1,D4", [string]$Outlets = "submerged,free")
$Repo  = "D:\My Projects\Dam-Breach-Studio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log   = Join-Path ([Environment]::GetFolderPath("Desktop")) "onedim_b12d_diagnosis_$Stamp.log"
Set-Location (Join-Path $Repo "python")
python -B -u -m onedim.verification.b12d_diagnosis --tmax $TMax --configs $Configs --outlets $Outlets 2>&1 | Tee-Object -FilePath $Log
Write-Host "`nLog written to $Log"
