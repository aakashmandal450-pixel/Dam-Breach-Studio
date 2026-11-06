# Walsh S3 grid check on the H/24 grid (4 cm cells), with (c) headcut_min_slope = 0.1 + (f) angle-of-repose collapse.
#   (i)   f_t = 1  -> compare with (f) at H/16: 94 L/s, rise 160 s   (the first attempt hit MemoryError at 840 s)
#   (i2)  f_t = 3  -> compare with (g1) at H/16: 222 L/s, rise 70 s, width 1.58 m (observed 240 L/s, 73 s, ~1.6 m)
# Diagnostic only; Walsh is excluded, nothing is scored, engine file unchanged.
# One after the other on ONE core (the calibration re-run keeps the other five). About 1.5-2 h each.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_walsh_i.ps1"
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$env:OMP_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"; $env:OPENBLAS_NUM_THREADS = "1"
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "walsh_i_$(Get-Date -Format yyyyMMdd_HHmm).txt"
$base = @("--grid", "24", "--t-end", "900", "--log-every", "10", "--pilot-channel", "--pilot-depth", "0.12025",
          "--section-every", "30", "--max-wall", "21600", "--cfg", "headcut_min_slope=0.1", "--avalanche")
$runs = @(
    @{ Name = "(i) H/24, f_t 1";  Args = $base + @("--suffix", "_t900_i_H24") },
    @{ Name = "(i2) H/24, f_t 3"; Args = $base + @("--f-t", "3", "--suffix", "_t900_i2_H24_ft3") }
)
foreach ($r in $runs) {
    "`n===== $($r.Name)   started $(Get-Date -Format HH:mm:ss) =====" | Tee-Object -FilePath $log -Append
    python -u calibration\diag_walsh.py @($r.Args) 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
}
"`nAll done $(Get-Date -Format HH:mm:ss). Log: $log" | Tee-Object -FilePath $log -Append
