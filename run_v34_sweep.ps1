# V3.4 law sweep at calibration-scale factors - which mechanism over-widens the breach?
#
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_sweep.ps1"
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_sweep.ps1" -Factors f14best
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_sweep.ps1" -Factors 1,31.62
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_sweep.ps1" -Axes collapse_mode,headcut_face_slope
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_sweep.ps1" -SummaryOnly
#
# Sweeps ONE option at a time around the F1-F7 reference and reports Qp and B for each.
# The width defect is invisible at neutral factors, so this runs at cal-2's fitted
# factors by default (C_h 10, f_t 3.162) - where Castlewood's width reached 136.8 m
# against an observed 54.9 m.
#
# Read the B column within each axis. The axis whose options move B most is the
# mechanism responsible. collapse_mode (F5, bank_wedge) is the leading suspect.
#
# Named factor sets: cal2 | neutral | f14best | f567best   (or pass "C_h,f_t")

param(
    [int]$Workers = 6,
    [int]$Grid = 6,
    [int]$Grid2 = 0,
    [string]$Factors = "cal2",
    [string]$Axes = "",
    [switch]$SummaryOnly
)

$ErrorActionPreference = "Stop"

$Repo    = "D:\My Projects\Dam-Breach-Studio"
$PyDir   = Join-Path $Repo "python"
$Script  = "calibration\v34_law_sweep.py"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$Log     = Join-Path $Desktop "v34_sweep_${Factors}_H${Grid}_$Stamp.log"

if (-not (Test-Path (Join-Path $PyDir $Script))) {
    Write-Host "ERROR: cannot find $Script under $PyDir" -ForegroundColor Red
    exit 1
}
Set-Location $PyDir

$runArgs = @("-u", $Script, "--case", "Castlewood", "--grid", $Grid,
             "--factors", $Factors, "--workers", $Workers, "--desktop", $Desktop)
if ($Grid2 -gt 0)  { $runArgs += @("--grid2", $Grid2) }
if ($Axes)         { $runArgs += @("--axes") + ($Axes -split "[,\s]+" | Where-Object { $_ }) }
if ($SummaryOnly)  { $runArgs += "--summary-only" }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  V3.4 law sweep - which mechanism over-widens the breach?" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  case    : Castlewood   (observed Qp 3570 m3/s, B 54.9 m)"
Write-Host "  grid    : H/$Grid$(if ($Grid2 -gt 0) { " and H/$Grid2" })"
Write-Host "  factors : $Factors$(if ($Factors -eq 'cal2') { '   (C_h 10, f_t 3.162 - cal-2 fitted)' })"
Write-Host "  axes    : $(if ($Axes) { $Axes } else { 'all 9' })"
Write-Host "  workers : $Workers"
Write-Host "  log     : $Log"
Write-Host ""
Write-Host "  Reference for comparison, Castlewood at cal-2 factors, H/6:" -ForegroundColor DarkGray
Write-Host "      old engine  B  52.6 m     F1-F4  B  94.7 m     F1-F7  B 136.8 m" -ForegroundColor DarkGray
Write-Host "  Read the B column within each axis; the axis that moves it owns the defect." -ForegroundColor DarkGray
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

$SumSrc = Join-Path $Repo "runs\v34_law_sweep\SUMMARY_Castlewood_$Factors.txt"
if (Test-Path $SumSrc) {
    $SumDst = Join-Path $Desktop "v34_sweep_summary_${Factors}_H${Grid}_$Stamp.txt"
    Copy-Item $SumSrc $SumDst -Force
    Write-Host ""
    Write-Host "Summary: $SumDst" -ForegroundColor Green
} else {
    Write-Host "No summary at $SumSrc - check the log: $Log" -ForegroundColor Yellow
}

Write-Host ""
if ($code -eq 0) { Write-Host "Done." -ForegroundColor Green }
else { Write-Host "Exited with code $code - see $Log" -ForegroundColor Yellow }
exit $code
