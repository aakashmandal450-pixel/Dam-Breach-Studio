# FELA roof bounds (v2): validity checks - Prandtl footing, circular tunnel vs Wilson et al. 2011, square pipe roof.
#   powershell -ExecutionPolicy Bypass -File ".\run_fela_benchmarks.ps1"
$ErrorActionPreference = "Continue"
$Repo    = "D:\My Projects\Dam-Breach-Studio"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$Log     = Join-Path $Desktop "fela_benchmarks_$Stamp.log"
$Ver     = Join-Path $Repo "python\lumped\verification"
Set-Location $Ver
Write-Host "FELA v2 benchmarks. Log: $Log" -ForegroundColor Cyan
& python -c "import cvxpy, clarabel" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing cvxpy + clarabel ..." -ForegroundColor Yellow
    & python -m pip install --quiet cvxpy clarabel scipy numpy
}
$sw = [Diagnostics.Stopwatch]::StartNew()
& python -B -u -W ignore fela_benchmarks.py (Join-Path $Ver "fela_benchmarks.txt") 2>&1 | Tee-Object -FilePath $Log
$code = $LASTEXITCODE
$res = if ($code -eq 0) { "PASS" } else { "FAIL" }
"`n$res  (exit $code, $([int]$sw.Elapsed.TotalSeconds) s)" | Tee-Object -FilePath $Log -Append
exit $code
