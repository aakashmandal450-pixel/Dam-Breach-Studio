# Verification matrix of the expansion-stability note (V1 prediction, V2 grid spacing, V3 direction,
# V4 reconstruction). Prints each case as it finishes; log to the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_b12d_theory_check.ps1
#         powershell -ExecutionPolicy Bypass -File .\run_b12d_theory_check.ps1 -Tests V1,V3   (subset)
param([string]$Tests = "V1,V2,V3,V4")
$Repo  = "D:\My Projects\Dam-Breach-Studio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log   = Join-Path ([Environment]::GetFolderPath("Desktop")) "onedim_b12d_theory_check_$Stamp.log"
Set-Location (Join-Path $Repo "python")
python -B -u -m onedim.verification.b12d_theory_check --tests $Tests 2>&1 | Tee-Object -FilePath $Log
Write-Host "`nLog written to $Log"
