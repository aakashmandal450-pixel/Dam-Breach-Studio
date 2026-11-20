# V3.4 isolation test 3 - which of F5 / F6 / F7 collapses the breach?
# Runs LaurelRun + Castlewood at H/9 and H/12 over the fix ladder (base -> f5 -> f56 -> f567)
# plus two leave-one-out variants. Resumable: re-run this script to pick up where it stopped.
#
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_f567.ps1"
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_f567.ps1" -LadderOnly
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_f567.ps1" -SummaryOnly

param(
    [int]$Workers = 6,
    [switch]$LadderOnly,
    [switch]$SummaryOnly
)

$ErrorActionPreference = "Stop"

$Repo    = "D:\My Projects\Dam-Breach-Studio"
$PyDir   = Join-Path $Repo "python"
$Script  = "calibration\v34_isolation_f567.py"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$Log     = Join-Path $Desktop "v34_f567_isolation_$Stamp.log"

if (-not (Test-Path (Join-Path $PyDir $Script))) {
    Write-Host "ERROR: cannot find $Script under $PyDir" -ForegroundColor Red
    Write-Host "Save v34_isolation_f567.py into: $(Join-Path $PyDir 'calibration')" -ForegroundColor Yellow
    exit 1
}

Set-Location $PyDir

$runArgs = @("-u", $Script, "--workers", $Workers, "--desktop", $Desktop)
if ($LadderOnly)  { $runArgs += "--ladder-only" }
if ($SummaryOnly) { $runArgs += "--summary-only" }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  V3.4 isolation test 3 - F5 / F6 / F7 regression hunt" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  cases   : LaurelRun, Castlewood"
Write-Host "  grids   : H/9, H/12"
if ($LadderOnly) {
    Write-Host "  variants: base, f5, f56, f567            (16 runs)"
} else {
    Write-Host "  variants: base, f5, f56, f567, no_f5, no_f6   (24 runs)"
}
Write-Host "  workers : $Workers        cap: 2 h per run"
Write-Host "  log     : $Log"
Write-Host ""
Write-Host "  Resumable - finished runs are skipped on a re-run." -ForegroundColor DarkGray
Write-Host "  The ladder runs first, so the cliff usually shows before the end." -ForegroundColor DarkGray
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

$elapsed = (Get-Date) - $t0

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ("  Wall time: {0:hh\:mm\:ss}" -f $elapsed) -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# Copy the python-side summary next to the log
$SumSrc = Join-Path $Repo "runs\v34_isolation_f567\SUMMARY.txt"
if (Test-Path $SumSrc) {
    $SumDst = Join-Path $Desktop "v34_f567_isolation_summary_$Stamp.txt"
    Copy-Item $SumSrc $SumDst -Force
    Write-Host ""
    Write-Host "Summary: $SumDst" -ForegroundColor Green
    Write-Host ""
    Get-Content $SumDst | Write-Host
} else {
    Write-Host "No SUMMARY.txt produced - check the log: $Log" -ForegroundColor Yellow
}

Write-Host ""
if ($code -eq 0) {
    Write-Host "Done." -ForegroundColor Green
} else {
    Write-Host "Exited with code $code - see $Log" -ForegroundColor Yellow
}
exit $code
