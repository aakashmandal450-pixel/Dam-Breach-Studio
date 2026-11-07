# Numba backend check: (1) compares fast_hydro (Numba) with the NumPy engine on every calibration case, Walsh S3,
# the non-default options and the second-order scheme; (2) runs the four V3.2 test suites with Numba switched on.
# Writes a pass/fail log to the Desktop. Read-only: the calibration grid and the engine file are not touched.
# One process, about 35-45 min. Run it next to the calibration re-run if you like.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_fast_check.ps1"
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
$env:OMP_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"; $env:OPENBLAS_NUM_THREADS = "1"
New-Item -ItemType Directory -Force -Path (Join-Path $root "tmp") | Out-Null
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "fast_check_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"Numba backend check  $(Get-Date -Format s)" | Tee-Object -FilePath $log

python -c "import numba" 2>$null
if ($LASTEXITCODE -ne 0) {
    "numba is not installed; installing it now (python -m pip install numba) ..." | Tee-Object -FilePath $log -Append
    python -m pip install numba 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
}

$summary = @()
"`n##### PART 1: Numba vs NumPy on short runs #####" | Tee-Object -FilePath $log -Append
python -u calibration\compare_fast.py 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
$summary += ("{0,-60} {1}" -f "Part 1: Numba vs NumPy comparison", $(if ($LASTEXITCODE -eq 0) { "PASS" } else { "FAIL (exit $LASTEXITCODE)" }))

"`n##### PART 2: V3.2 test suites with the Numba backend #####" | Tee-Object -FilePath $log -Append
$suites = @("tests\v3_engine_regression.py", "tests\v3_2_feature_tests.py", "tests\v3_2_1_reservoir_tests.py", "tests\v3_2_2_step0_tests.py")
foreach ($s in $suites) {
    "`n===== $s (Numba) =====" | Tee-Object -FilePath $log -Append
    $sw = [Diagnostics.Stopwatch]::StartNew()
    python -u tests\run_with_fast.py $s 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
    $code = $LASTEXITCODE; $sw.Stop()
    $summary += ("{0,-60} {1}  [{2:N0} s]" -f "Part 2: $s", $(if ($code -eq 0) { "PASS" } else { "FAIL (exit $code)" }), $sw.Elapsed.TotalSeconds)
}

"`n===== SUMMARY =====" | Tee-Object -FilePath $log -Append
$summary | Tee-Object -FilePath $log -Append
"Log: $log" | Tee-Object -FilePath $log -Append
