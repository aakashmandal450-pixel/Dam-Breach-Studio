# V3.4 three-grid convergence study: H/9, H/12, H/15 on F1-F7
#
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_convergence.ps1"
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_convergence.ps1" -WithBase
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_convergence.ps1" -SummaryOnly
#
# 2026-11-19: B_eq (grid-independent width) + the headcut_gate = cell variant, fresh runs:
#   powershell -ExecutionPolicy Bypass -File ".\run_v34_convergence.ps1" -Tag beq -Variants f567,cell -Workers 6
# -Tag writes to runs\v34_convergence_<tag> and reruns everything (old results have no B_eq).
#
# The H/9 and H/12 results are reused from runs\v34_isolation_f567, so only the two
# H/15 runs are new. Resumable: re-run to pick up where it stopped.

param(
    [int]$Workers = 2,
    [switch]$WithBase,
    [switch]$SummaryOnly,
    [string]$Tag = "",
    [string[]]$Variants = @()
)

$ErrorActionPreference = "Stop"

$Repo    = "D:\My Projects\Dam-Breach-Studio"
$PyDir   = Join-Path $Repo "python"
$Script  = "calibration\v34_convergence.py"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$TagSfx  = if ($Tag) { "_$Tag" } else { "" }
$Log     = Join-Path $Desktop "v34_convergence${TagSfx}_$Stamp.log"

if (-not (Test-Path (Join-Path $PyDir $Script))) {
    Write-Host "ERROR: cannot find $Script under $PyDir" -ForegroundColor Red
    exit 1
}
Set-Location $PyDir

$runArgs = @("-u", $Script, "--workers", $Workers, "--desktop", $Desktop)
if ($WithBase)    { $runArgs += "--with-base" }
if ($SummaryOnly) { $runArgs += "--summary-only" }
if ($Tag)         { $runArgs += @("--tag", $Tag) }
if ($Variants.Count -gt 0) { $runArgs += "--variants"; $runArgs += ($Variants -split ",") }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  V3.4 grid convergence - H/9, H/12, H/15" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  cases    : LaurelRun, Castlewood"
if ($Variants.Count -gt 0) { Write-Host "  variants : $($Variants -join ', ')" }
else { Write-Host "  variant  : f567 (F1-F7)$(if ($WithBase) { ' + base (F1-F4)' })" }
if ($Tag) { Write-Host "  results  : runs\v34_convergence_$Tag  (fresh: all grids rerun, with B_eq)" }
else { Write-Host "  new runs : 2 at H/15$(if ($WithBase) { ' (4 with -WithBase)' })  - H/9 and H/12 are reused" }
Write-Host "  workers  : $Workers        cap: 4 h per run"
Write-Host "  log      : $Log"
Write-Host ""
Write-Host "  H/15 is ~1.6x the cells of H/12, so expect roughly 2x its runtime." -ForegroundColor DarkGray
Write-Host "  Reports Qp, width, time-to-peak and max lowering, with observed order and GCI." -ForegroundColor DarkGray
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

$SumSrc = Join-Path $Repo "runs\v34_convergence$TagSfx\SUMMARY.txt"
if (Test-Path $SumSrc) {
    $SumDst = Join-Path $Desktop "v34_convergence_summary${TagSfx}_$Stamp.txt"
    Copy-Item $SumSrc $SumDst -Force
    Write-Host ""
    Write-Host "Summary: $SumDst" -ForegroundColor Green
} else {
    Write-Host "No SUMMARY.txt produced - check the log: $Log" -ForegroundColor Yellow
}

Write-Host ""
if ($code -eq 0) { Write-Host "Done." -ForegroundColor Green }
else { Write-Host "Exited with code $code - see $Log" -ForegroundColor Yellow }
exit $code
