# Distributed 1-D engine, phase B first gates. Prints progress live and writes a log to the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_onedim_phaseB.ps1          (full, long)
#         powershell -ExecutionPolicy Bypass -File .\run_onedim_phaseB.ps1 -Quick   (smaller grids)
param([switch]$Quick)
$Repo  = "D:\My Projects\Dam-Breach-Studio"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Log   = Join-Path ([Environment]::GetFolderPath("Desktop")) "onedim_phaseB_$Stamp.log"
Set-Location (Join-Path $Repo "python")
python -c "import numpy, scipy" 2>$null
if ($LASTEXITCODE -ne 0) { python -m pip install numpy scipy }
$args = @("-B", "-u", "-m", "onedim.verification.run_phase_b")
if ($Quick) { $args += "--quick" }
python @args 2>&1 | Tee-Object -FilePath $Log
Write-Host "`nLog written to $Log"
