# V3.3 engine tests: the four V3.2 suites (defaults must reproduce V3.2.2) plus the new V3.3 checks,
# each with the NumPy engine and with the Numba backend. Writes a pass/fail log to the Desktop. A few minutes.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_v33_tests.ps1"
$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force -Path (Join-Path $root "tmp") | Out-Null
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "v33_tests_$(Get-Date -Format yyyyMMdd_HHmm).txt"
"V3.3 test run  $(Get-Date -Format s)   python: $(python --version 2>&1)" | Tee-Object -FilePath $log
$suites = @("tests\v3_engine_regression.py", "tests\v3_2_feature_tests.py", "tests\v3_2_1_reservoir_tests.py",
            "tests\v3_2_2_step0_tests.py", "tests\v3_3_tests.py")
$summary = @(); $overall = 0
foreach ($backend in @("NumPy", "Numba")) {
    foreach ($s in $suites) {
        "`n===== $s ($backend) =====" | Tee-Object -FilePath $log -Append
        $sw = [Diagnostics.Stopwatch]::StartNew()
        if ($backend -eq "NumPy") { python -u $s 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append }
        else { python -u tests\run_with_fast.py $s 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append }
        $code = $LASTEXITCODE; $sw.Stop()
        if ($code -ne 0) { $overall = 1 }
        $summary += ("{0,-38} {1,-6} {2}  [{3:N0} s]" -f $s, $backend, $(if ($code -eq 0) { "PASS" } else { "FAIL (exit $code)" }), $sw.Elapsed.TotalSeconds)
    }
}
"`n===== SUMMARY =====" | Tee-Object -FilePath $log -Append
$summary | Tee-Object -FilePath $log -Append
$(if ($overall -eq 0) { "ALL PASS" } else { "SOME FAILED" }) | Tee-Object -FilePath $log -Append
"Log: $log" | Tee-Object -FilePath $log -Append
exit $overall
