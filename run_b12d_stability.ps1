# B12d linear stability analysis: spectral radius of the explicit step against CFL, critical CFL,
# and the shape of the worst mode, for the conduit outlet and five comparison cases.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_b12d_stability.ps1
#         powershell -ExecutionPolicy Bypass -File .\run_b12d_stability.ps1 -Cases outlet,uniform
param([string]$Cases = "outlet,outlet_as100,outlet_b04,pp,fs,uniform")
$Repo  = "D:\My Projects\Dam-Breach-Studio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log   = Join-Path ([Environment]::GetFolderPath("Desktop")) "onedim_b12d_stability_$Stamp.log"
Set-Location (Join-Path $Repo "python")
python -B -u -m onedim.verification.b12d_stability --cases $Cases 2>&1 | Tee-Object -FilePath $Log
Write-Host "`nLog written to $Log"
