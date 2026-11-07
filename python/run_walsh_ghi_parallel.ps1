# Walsh S3 diagnostics (g)-(i), all FIVE runs at once (one process each). Same runs as run_walsh_ghi.ps1.
# Diagnostic only; Walsh is excluded, nothing is scored, engine file unchanged.
# Note: with the calibration re-run (5 workers) this puts 10 processes on 6 cores, so everything runs slower while
# these are going (the re-run's CPU-time budget is not affected; only its wall time).
# Logs: one file per run on the Desktop (walsh_<run>_<time>.txt); this window prints progress every 2 min.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_walsh_ghi_parallel.ps1"
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$env:OMP_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"; $env:OPENBLAS_NUM_THREADS = "1"
$desk = [Environment]::GetFolderPath("Desktop"); $stamp = Get-Date -Format yyyyMMdd_HHmm
$base = @("-u", "calibration\diag_walsh.py", "--t-end", "900", "--log-every", "10", "--pilot-channel", "--pilot-depth", "0.12025",
          "--section-every", "30", "--max-wall", "21600", "--cfg", "headcut_min_slope=0.1", "--avalanche")
$runs = [ordered]@{
    "g1_ft3"       = @("--grid", "16", "--f-t", "3", "--suffix", "_t900_g1_ft3")
    "g2_ft10"      = @("--grid", "16", "--f-t", "10", "--suffix", "_t900_g2_ft10")
    "h1_phi30.5"   = @("--grid", "16", "--phi-deg", "30.5", "--suffix", "_t900_h1_phi30.5")
    "h2_dry45"     = @("--grid", "16", "--phi-deg", "30.5", "--avalanche-dry-deg", "45", "--avalanche-hswitch", "0.1", "--suffix", "_t900_h2_dry45")
    "i_H24"        = @("--grid", "24", "--suffix", "_t900_i_H24")
}
$procs = @{}
foreach ($k in $runs.Keys) {
    $out = Join-Path $desk "walsh_${k}_$stamp.txt"; $err = Join-Path $desk "walsh_${k}_${stamp}_err.txt"
    $argline = ($base + $runs[$k] | ForEach-Object { if ($_ -match '\s') { "`"$_`"" } else { $_ } }) -join " "
    $procs[$k] = @{ P = (Start-Process python -ArgumentList $argline -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err); Out = $out }
    "started $k  (log: $out)"
}
while ($true) {
    Start-Sleep -Seconds 120
    $running = @($procs.Keys | Where-Object { -not $procs[$_].P.HasExited })
    "--- $(Get-Date -Format HH:mm:ss)  running: $($running.Count) of $($procs.Count)"
    foreach ($k in $procs.Keys) {
        $last = Get-Content $procs[$k].Out -Tail 1 -ErrorAction SilentlyContinue
        "    {0,-12} {1}" -f $k, ($(if ($procs[$k].P.HasExited) { "finished" } else { $last }))
    }
    if ($running.Count -eq 0) { break }
}
"`nAll done $(Get-Date -Format HH:mm:ss). Logs: $desk\walsh_*_$stamp.txt"
