# Walsh S3 stage-3 sensitivity (diagnostic only; Walsh is excluded, nothing is scored, engine file unchanged).
# Baseline for comparison: runs\diag_walsh\WalshS3_H16_pilot0.37m_t900_*  (22 L/s peak at 450 s)
#   (a) no capacity reduction where flow runs uphill (slope-factor lower clip 0.3 -> 1.0)
#   (c) headcut scarp threshold 0.5 -> 0.1
# Runs one after the other on ONE core (the calibration re-run keeps the other five). About 20-25 min each.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_walsh_ac.ps1"
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "walsh_ac_$(Get-Date -Format yyyyMMdd_HHmm).txt"
$common = @("--grid", "16", "--t-end", "900", "--log-every", "10", "--pilot-channel", "--section-every", "30", "--max-wall", "5400")
$runs = @(
    @{ Name = "(a) uphill slope factor not reduced"; Args = $common + @("--uphill-floor", "1.0", "--suffix", "_t900_a_uphill1") },
    @{ Name = "(c) headcut_min_slope 0.1";          Args = $common + @("--cfg", "headcut_min_slope=0.1", "--suffix", "_t900_c_hc0.1") }
)
foreach ($r in $runs) {
    "`n===== $($r.Name)   started $(Get-Date -Format HH:mm:ss) =====" | Tee-Object -FilePath $log -Append
    python -u calibration\diag_walsh.py @($r.Args) 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
}
"`nAll done $(Get-Date -Format HH:mm:ss). Log: $log" | Tee-Object -FilePath $log -Append
