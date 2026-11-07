# Walsh S3 stage-3 test (f): angle-of-repose bank collapse (diagnostic only; Walsh is excluded, nothing is scored,
# engine file unchanged - the collapse rule is patched inside this process).
# Keeps (c) headcut_min_slope = 0.1. Compare with runs\diag_walsh\WalshS3_H16_pilot0.37m_t900_c_hc0.1_*
#   (50 L/s at 320 s, width 1.08 m). Observed: 240 L/s at 73 s, width about 1.6 m.
# ONE core, about 20-25 min.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_walsh_f.ps1"
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "walsh_f_$(Get-Date -Format yyyyMMdd_HHmm).txt"
$args_f = @("--grid", "16", "--t-end", "900", "--log-every", "10", "--pilot-channel", "--section-every", "30",
            "--max-wall", "5400", "--cfg", "headcut_min_slope=0.1", "--avalanche", "--suffix", "_t900_f_hc0.1_aval")
"===== (f) headcut 0.1 + angle-of-repose collapse   started $(Get-Date -Format HH:mm:ss) =====" | Tee-Object -FilePath $log
python -u calibration\diag_walsh.py @args_f 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
"`nAll done $(Get-Date -Format HH:mm:ss). Log: $log" | Tee-Object -FilePath $log -Append
