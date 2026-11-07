# Walsh S3 stage-3 diagnostics (g)-(i) (diagnostic only; Walsh is excluded, nothing is scored, engine file unchanged).
# All runs: (c) headcut_min_slope = 0.1 + (f) angle-of-repose collapse, pilot channel 0.37 x 0.12 m (depth fixed so
# every run starts from the same geometry). Reference: runs\diag_walsh\WalshS3_H16_pilot0.37m_t900_f_hc0.1_aval_*
#   (94 L/s at 230 s, width 1.33 m). Observed 240 L/s, rise 73 s, width about 1.6 m.
#   (g1) f_t = 3            (g2) f_t = 10                       -> is the remaining gap the erosion rate?
#   (h1) phi 30.5 deg (measured repose angle)
#   (h2) phi 30.5, dry slopes up to 45 deg (XBeach dryslp 1.0), wet = 30.5, wet/dry switch depth 0.1 m (XBeach hswitch)
#   (i)  as (f) on the H/24 grid (4 cm cells)                   -> grid dependence
# One after the other on ONE core. About 25 min each for (g)/(h), about 1.5 h for (i): roughly 3-3.5 h in total.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_walsh_ghi.ps1"
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "walsh_ghi_$(Get-Date -Format yyyyMMdd_HHmm).txt"
$base = @("--t-end", "900", "--log-every", "10", "--pilot-channel", "--pilot-depth", "0.12025", "--section-every", "30",
          "--max-wall", "14400", "--cfg", "headcut_min_slope=0.1", "--avalanche")
$runs = @(
    @{ Name = "(g1) f_t 3";  Args = @("--grid", "16") + $base + @("--f-t", "3",  "--suffix", "_t900_g1_ft3") },
    @{ Name = "(g2) f_t 10"; Args = @("--grid", "16") + $base + @("--f-t", "10", "--suffix", "_t900_g2_ft10") },
    @{ Name = "(h1) phi 30.5"; Args = @("--grid", "16") + $base + @("--phi-deg", "30.5", "--suffix", "_t900_h1_phi30.5") },
    @{ Name = "(h2) phi 30.5, dry 45, hswitch 0.1"; Args = @("--grid", "16") + $base + @("--phi-deg", "30.5", "--avalanche-dry-deg", "45", "--avalanche-hswitch", "0.1", "--suffix", "_t900_h2_dry45") },
    @{ Name = "(i) H/24";    Args = @("--grid", "24") + $base + @("--suffix", "_t900_i_H24") }
)
foreach ($r in $runs) {
    "`n===== $($r.Name)   started $(Get-Date -Format HH:mm:ss) =====" | Tee-Object -FilePath $log -Append
    python -u calibration\diag_walsh.py @($r.Args) 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
}
"`nAll done $(Get-Date -Format HH:mm:ss). Log: $log" | Tee-Object -FilePath $log -Append
