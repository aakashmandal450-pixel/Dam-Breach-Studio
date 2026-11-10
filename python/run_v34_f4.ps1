# V3.4 F4 check: (1) put the F4 files from _f4\ into place (only if F3 is committed), (2) all test suites with NumPy
# and Numba (run_v33_tests.ps1, a few minutes), (3) the grid-convergence check with F1+F2+F3+F4 (setup F1234:
# Castlewood + Laurel Run at H/6, H/9, H/12, neutral factors; 6 new runs, about 30-60 min; finished runs are skipped).
# Live progress in this window; full log and a results summary on the Desktop.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_v34_f4.ps1"
param([int]$Workers = 5)
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
$repo = Split-Path $root -Parent
$stage = Join-Path $repo "_f4"
Set-Location $root
$desk = [Environment]::GetFolderPath("Desktop")
$log = Join-Path $desk "v34_f4_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"V3.4 F4 check  $(Get-Date -Format s)   python: $(python --version 2>&1)   git: $(git -C $repo log --oneline -1)" | Tee-Object -FilePath $log

# ---- 1. install the F4 files -------------------------------------------------------------------------------------
$files = @(
    @("breach_engine_2d_v3_2.py", "python\breach_engine_2d_v3_2.py"),
    @("fast_morph.py",            "python\fast_morph.py"),
    @("v3_4_tests.py",            "python\tests\v3_4_tests.py"),
    @("v34_grid_check.py",        "python\calibration\v34_grid_check.py"),
    @("V3_2_CHANGELOG.md",        "python\V3_2_CHANGELOG.md"))
$need = $false
foreach ($f in $files) {
    $src = Join-Path $stage $f[0]; $dst = Join-Path $repo $f[1]
    if (-not (Test-Path $src)) { "STOP: missing $src" | Tee-Object -FilePath $log -Append; exit 2 }
    if ((Get-FileHash $src -Algorithm MD5).Hash -ne (Get-FileHash $dst -Algorithm MD5).Hash) { $need = $true }
}
if ($need) {
    $paths = $files | ForEach-Object { $_[1].Replace("\", "/") }
    $dirty = git -C $repo status --porcelain -- $paths
    if ($dirty) {
        "STOP: these files have uncommitted changes. Commit F3 first (see the chat), then run this script again:" | Tee-Object -FilePath $log -Append
        $dirty | ForEach-Object { "  $_" } | Tee-Object -FilePath $log -Append
        exit 2
    }
    foreach ($f in $files) {
        $src = Join-Path $stage $f[0]; $dst = Join-Path $repo $f[1]
        Copy-Item $src $dst -Force
        $ok = (Get-FileHash $src -Algorithm MD5).Hash -eq (Get-FileHash $dst -Algorithm MD5).Hash
        ("installed {0,-40} md5 {1}" -f $f[1], $(if ($ok) { "ok" } else { "MISMATCH" })) | Tee-Object -FilePath $log -Append
        if (-not $ok) { "STOP: copy failed for $($f[1])" | Tee-Object -FilePath $log -Append; exit 2 }
    }
} else { "F4 files already in place (md5 equal)" | Tee-Object -FilePath $log -Append }

# ---- 2. all test suites, NumPy and Numba -------------------------------------------------------------------------
"`n===== all test suites (run_v33_tests.ps1) =====" | Tee-Object -FilePath $log -Append
powershell -ExecutionPolicy Bypass -File (Join-Path $root "run_v33_tests.ps1") 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
if ($LASTEXITCODE -ne 0) {
    "TESTS FAILED - the grid check was not started. Log: $log" | Tee-Object -FilePath $log -Append
    exit 1
}

# ---- 3. grid-convergence check -----------------------------------------------------------------------------------
"`n===== grid-convergence check, setup F1234 (calibration\v34_grid_check.py) =====" | Tee-Object -FilePath $log -Append
$sw = [Diagnostics.Stopwatch]::StartNew()
python -u calibration\v34_grid_check.py --workers $Workers --desktop $desk 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
$code = $LASTEXITCODE
("grid check finished in {0:N1} min" -f $sw.Elapsed.TotalMinutes) | Tee-Object -FilePath $log -Append
$(if ($code -eq 0) { "ALL DONE (tests passed)" } else { "GRID CHECK FAILED - see above" }) | Tee-Object -FilePath $log -Append
"Log: $log   Summary: Desktop\v34_gridcheck_summary_*.txt   Runs: ..\runs\v34_gridcheck\" | Tee-Object -FilePath $log -Append
exit $code
