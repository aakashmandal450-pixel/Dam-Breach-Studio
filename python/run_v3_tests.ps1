# Runs the V3.2 regression and feature checks locally and writes a pass/fail log to the Desktop.
# Layout:  <root>\breach_engine_2d_v3_2.py
#          <root>\tests\v3_engine_regression.py
#          <root>\tests\v3_2_feature_tests.py
#          <root>\run_v3_tests.ps1   (this file)
# Usage:   powershell -ExecutionPolicy Bypass -File .\run_v3_tests.ps1

$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root
New-Item -ItemType Directory -Force -Path (Join-Path $root "tmp") | Out-Null

$desktop = [Environment]::GetFolderPath("Desktop")
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $desktop "v3_2_test_log_$stamp.txt"

$py = $null
foreach ($candidate in @("python", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) { $py = $candidate; break }
}
if (-not $py) { "No python or py launcher found on PATH." | Tee-Object -FilePath $log; exit 2 }

$suites = @(
    @{ Name = "V3 regression (conservation, restart, wave, headcut, formulas)"; Script = "tests\v3_engine_regression.py" },
    @{ Name = "V3.2 feature checks"; Script = "tests\v3_2_feature_tests.py" },
    @{ Name = "V3.2.1 reservoir positivity checks"; Script = "tests\v3_2_1_reservoir_tests.py" },
    @{ Name = "V3.2.2 Step 0 checks"; Script = "tests\v3_2_2_step0_tests.py" }
)

"V3.2 test run  $(Get-Date -Format s)" | Out-File -FilePath $log -Encoding utf8
"python: $(& $py --version 2>&1)" | Out-File -FilePath $log -Append -Encoding utf8
"root:   $root" | Out-File -FilePath $log -Append -Encoding utf8

$summary = @()
$overall = 0
foreach ($suite in $suites) {
    "" | Out-File -FilePath $log -Append -Encoding utf8
    "===== $($suite.Name) =====" | Tee-Object -FilePath $log -Append
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $output = cmd /c "$py `"$($suite.Script)`" 2>&1"
    $code = $LASTEXITCODE
    $sw.Stop()
    $output | Out-File -FilePath $log -Append -Encoding utf8
    $status = if ($code -eq 0) { "PASS" } else { "FAIL (exit $code)" }
    if ($code -ne 0) { $overall = 1 }
    $line = "{0,-70} {1}  [{2:N1} s]" -f $suite.Name, $status, $sw.Elapsed.TotalSeconds
    $summary += $line
    $line | Tee-Object -FilePath $log -Append
}

"" | Out-File -FilePath $log -Append -Encoding utf8
"===== SUMMARY =====" | Tee-Object -FilePath $log -Append
$summary | Tee-Object -FilePath $log -Append
"Log written to: $log" | Tee-Object -FilePath $log -Append
exit $overall
