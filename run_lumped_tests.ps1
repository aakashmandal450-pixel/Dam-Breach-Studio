# Lumped 1-D model: run the whole test suite and write a pass/fail log to the Desktop.
#
#   powershell -ExecutionPolicy Bypass -File ".\run_lumped_tests.ps1"

$ErrorActionPreference = "Stop"

$Repo    = "D:\My Projects\Dam-Breach-Studio"
$PyDir   = Join-Path $Repo "python"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$Log     = Join-Path $Desktop "lumped_tests_$Stamp.log"

Set-Location $PyDir
$branch = (& git -C $Repo branch --show-current) 2>$null
$commit = (& git -C $Repo rev-parse --short HEAD) 2>$null

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Lumped 1-D model - test suite" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  branch : $branch   commit: $commit"
Write-Host "  log    : $Log"
Write-Host ""

$t0 = Get-Date
"branch $branch  commit $commit  started $t0" | Out-File -FilePath $Log -Encoding utf8
try {
    & python -B -u -m lumped.tests.run_all 2>&1 | Tee-Object -FilePath $Log -Append
    $code = $LASTEXITCODE
} catch {
    Write-Host "RUN FAILED: $_" -ForegroundColor Red
    "RUN FAILED: $_" | Out-File -FilePath $Log -Append
    $code = 1
}

Write-Host ""
Write-Host ("  Wall time: {0:hh\:mm\:ss}" -f ((Get-Date) - $t0)) -ForegroundColor Cyan
if ($code -eq 0) { Write-Host "  ALL TESTS PASSED" -ForegroundColor Green }
else { Write-Host "  TESTS FAILED (exit $code) - see $Log" -ForegroundColor Red }
exit $code
