# Part 5 stability table: crater-equation checks, table build (resumable), acceptance test.
#
#   powershell -ExecutionPolicy Bypass -File ".\run_stability_table.ps1"                     # everything
#   powershell -ExecutionPolicy Bypass -File ".\run_stability_table.ps1" -Stage checks       # crater checks only (seconds)
#   powershell -ExecutionPolicy Bypass -File ".\run_stability_table.ps1" -Stage table -Grid pilot   # 32-point timing run
#   powershell -ExecutionPolicy Bypass -File ".\run_stability_table.ps1" -Stage table        # full 936-point table
#   powershell -ExecutionPolicy Bypass -File ".\run_stability_table.ps1" -Stage accept       # acceptance test
#   add  -Workers 4  to set the number of parallel solves (default: cores - 1, at most 6)
#
# The table build is resumable: stop it any time (Ctrl+C) and run the same command again; finished
# points are kept in python\lumped\verification\stability_table.csv. The pilot points are part of the
# full grid, so a pilot run is not wasted.
param(
    [ValidateSet("all", "checks", "table", "accept")] [string]$Stage = "all",
    [ValidateSet("full", "pilot")] [string]$Grid = "full",
    [int]$Workers = 0
)
$ErrorActionPreference = "Continue"
$Repo    = "D:\My Projects\Dam-Breach-Studio"
$Ver     = Join-Path $Repo "python\lumped\verification"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"
$Log     = Join-Path $Desktop "stability_table_${Stage}_$Stamp.log"
$Table   = Join-Path $Ver "stability_table.csv"
$Accept  = Join-Path $Ver "table_acceptance.csv"
Set-Location $Ver

function Say($msg, $color = "Cyan") {
    Write-Host $msg -ForegroundColor $color
    Add-Content -Path $Log -Value $msg -Encoding UTF8
}
function RunPy($label, [string[]]$pyargs) {
    Say "`n===== $label  ($(Get-Date -Format 'HH:mm:ss')) ====="
    # every line goes to the screen and to the log (UTF-8); nothing leaks into the return value
    & python -B -u -W ignore @pyargs 2>&1 | ForEach-Object {
        $line = "$_"
        Add-Content -Path $Log -Value $line -Encoding UTF8
        Write-Host $line
    }
    $code = $LASTEXITCODE
    if ($code -eq 0) { Say "----- $label : PASS" "Green" } else { Say "----- $label : FAIL (exit $code)" "Red" }
    return $code
}

Say "Part 5 stability table run - stage '$Stage', grid '$Grid'. Log: $Log"
& python -c "import cvxpy, clarabel, scipy, numpy" 2>$null
if ($LASTEXITCODE -ne 0) {
    Say "Installing cvxpy, clarabel, scipy, numpy ..." "Yellow"
    & python -m pip install --quiet cvxpy clarabel scipy numpy
}
$sw = [Diagnostics.Stopwatch]::StartNew()
$results = [ordered]@{}
$wargs = @(); if ($Workers -gt 0) { $wargs = @("--workers", "$Workers") }

if ($Stage -in @("all", "checks")) {
    $results["crater-equation checks"] = RunPy "1. Crater-equation checks (walls, pore water, obstruction, water balance)" @("crater_balance_check.py")
}
if ($Stage -in @("all", "table")) {
    $results["stability table ($Grid)"] = RunPy "2. Stability table build, grid '$Grid' (resumable)" (@("build_stability_table.py", "--grid", $Grid, "--out", $Table) + $wargs)
}
if ($Stage -in @("all", "accept")) {
    if (Test-Path $Table) {
        $results["table acceptance"] = RunPy "3. Table acceptance test (direct solves vs table)" (@("table_acceptance.py", "--table", $Table, "--out", $Accept) + $wargs)
    } else {
        Say "3. Table acceptance test skipped: $Table not found (build the table first)." "Yellow"
        $results["table acceptance"] = 1
    }
}

Say "`n===== SUMMARY ($([int]$sw.Elapsed.TotalMinutes) min) ====="
$allok = $true
foreach ($k in $results.Keys) {
    $ok = ($results[$k] -eq 0); if (-not $ok) { $allok = $false }
    Say ("  {0,-34} {1}" -f $k, $(if ($ok) { "PASS" } else { "FAIL" })) $(if ($ok) { "Green" } else { "Red" })
}
Say $(if ($allok) { "OVERALL: PASS" } else { "OVERALL: FAIL" }) $(if ($allok) { "Green" } else { "Red" })
Say "Table: $Table`nAcceptance details: $Accept"
exit $(if ($allok) { 0 } else { 1 })
