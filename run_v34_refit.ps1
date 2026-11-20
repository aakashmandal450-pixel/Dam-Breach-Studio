# V3.4 Castlewood factor refit on the F1-F7 engine
#
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_refit.ps1"
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_refit.ps1" -Full          # all 42 cells
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_refit.ps1" -Grid 9        # confirm finer
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_refit.ps1" -SummaryOnly
#
# Default: 5 x 5 = 25 cells at H/6 (the protocol field-case calibration grid), roughly
# 4 min a cell, so about 1.5 h on 2 workers. Resumable - re-run to continue.
#
# Wait for the convergence job to finish before starting this; both are CPU bound.

param(
    [int]$Workers = 2,
    [int]$Grid = 6,
    [ValidateSet("f567","base")]
    [string]$Variant = "f567",
    [switch]$Full,
    [switch]$SummaryOnly
)

$ErrorActionPreference = "Stop"

$Repo    = "D:\My Projects\Dam-Breach-Studio"
$PyDir   = Join-Path $Repo "python"
$Script  = "calibration\v34_castlewood_refit.py"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$Log     = Join-Path $Desktop "v34_refit_${Variant}_H${Grid}_$Stamp.log"

if (-not (Test-Path (Join-Path $PyDir $Script))) {
    Write-Host "ERROR: cannot find $Script under $PyDir" -ForegroundColor Red
    exit 1
}
Set-Location $PyDir

$runArgs = @("-u", $Script, "--workers", $Workers, "--grid", $Grid, "--variant", $Variant, "--desktop", $Desktop)
if ($Full)        { $runArgs += "--full" }
if ($SummaryOnly) { $runArgs += "--summary-only" }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  V3.4 Castlewood factor refit - F1-F7 engine" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  case    : Castlewood   (observed Qp 3570 m3/s, B 54.9 m)"
Write-Host "  variant : $Variant$(if ($Variant -eq 'base') { '   (F1-F4 only - F5/F6/F7 OFF)' } else { '   (F1-F7)' })"
Write-Host "  grid    : H/$Grid$(if ($Grid -eq 6) { '  (protocol field-case calibration grid)' })"
Write-Host "  cells   : $(if ($Full) { '6 x 7 = 42 (full old grid)' } else { '5 x 5 = 25' })"
Write-Host "  workers : $Workers        cap: 2 h per cell"
Write-Host "  log     : $Log"
Write-Host ""
Write-Host "  Compares cell by cell against the pre-F1-F7 surface in runs\calibration_grid_cal2." -ForegroundColor DarkGray
Write-Host "  Result tells you HOW FAR the optimum moved - it is not a single-case fit to adopt." -ForegroundColor DarkGray
Write-Host ""

$t0 = Get-Date

try {
    & python @runArgs 2>&1 | Tee-Object -FilePath $Log
    $code = $LASTEXITCODE
} catch {
    Write-Host ""
    Write-Host "RUN FAILED: $_" -ForegroundColor Red
    $code = 1
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ("  Wall time: {0:hh\:mm\:ss}" -f ((Get-Date) - $t0)) -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

$SumSrc = Join-Path $Repo "runs\v34_castlewood_refit\SUMMARY_${Variant}_H$Grid.txt"
if (Test-Path $SumSrc) {
    $SumDst = Join-Path $Desktop "v34_refit_summary_${Variant}_H${Grid}_$Stamp.txt"
    Copy-Item $SumSrc $SumDst -Force
    Write-Host ""
    Write-Host "Summary: $SumDst" -ForegroundColor Green
} else {
    Write-Host "No summary produced - check the log: $Log" -ForegroundColor Yellow
}

Write-Host ""
if ($code -eq 0) { Write-Host "Done." -ForegroundColor Green }
else { Write-Host "Exited with code $code - see $Log" -ForegroundColor Yellow }
exit $code
