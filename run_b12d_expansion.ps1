# B12d expansion check: critical CFL for free->free, pressurised->free and pressurised->pressurised
# expansions under the same linearisation. Prints each case as it finishes; log to the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_b12d_expansion.ps1
$Repo  = "D:\My Projects\Dam-Breach-Studio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log   = Join-Path ([Environment]::GetFolderPath("Desktop")) "onedim_b12d_expansion_$Stamp.log"
Set-Location (Join-Path $Repo "python")
python -B -u -m onedim.verification.b12d_expansion 2>&1 | Tee-Object -FilePath $Log
Write-Host "`nLog written to $Log"
