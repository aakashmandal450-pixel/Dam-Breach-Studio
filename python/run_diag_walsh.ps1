# Walsh S3 initiation diagnostic: two runs with live progress, full log copied to the Desktop.
#   Run 1: cal-1 grid (H/8, 12.5 cm cells), 1800 s simulated, a line every 10 s   (about 5-10 min)
#   Run 2: fine grid (H/24, about 4 cm cells), 120 s simulated, a line every 5 s     (about 10 min)
# Read-only: it does not change the engine and does not touch runs\calibration_grid, so the grid can keep running.
# Usage (from the python folder):
#   powershell -ExecutionPolicy Bypass -File .\run_diag_walsh.ps1

$ErrorActionPreference = "Continue"
$root = $PSScriptRoot
Set-Location $root

$desktop = [Environment]::GetFolderPath("Desktop")
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$log = Join-Path $desktop "walsh_diag_log_$stamp.txt"

$py = $null
foreach ($candidate in @("python", "py")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) { $py = $candidate; break }
}
if (-not $py) { "No python or py launcher found on PATH." | Tee-Object -FilePath $log; exit 2 }

"Walsh S3 initiation diagnostic  $(Get-Date -Format s)" | Tee-Object -FilePath $log
"python: $(& $py --version 2>&1)" | Tee-Object -FilePath $log -Append

$runs = @(
    @{ Name = "Run 1 of 2: cal-1 grid H/8, 1800 s"; Args = @("--grid", "8", "--t-end", "1800", "--log-every", "10", "--max-wall", "2400") },
    @{ Name = "Run 2 of 2: fine grid H/24, 120 s"; Args = @("--grid", "24", "--t-end", "120", "--log-every", "5", "--max-wall", "2400") }
)

$total = [Diagnostics.Stopwatch]::StartNew()
foreach ($r in $runs) {
    "" | Tee-Object -FilePath $log -Append
    "===== $($r.Name)   started $(Get-Date -Format HH:mm:ss) =====" | Tee-Object -FilePath $log -Append
    $sw = [Diagnostics.Stopwatch]::StartNew()
    & $py -u "calibration\diag_walsh.py" @($r.Args) 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
    $code = $LASTEXITCODE
    "----- finished in $([math]::Round($sw.Elapsed.TotalMinutes, 1)) min, exit code $code -----" | Tee-Object -FilePath $log -Append
}
"" | Tee-Object -FilePath $log -Append
"All done in $([math]::Round($total.Elapsed.TotalMinutes, 1)) min. Results: ..\runs\diag_walsh\   Log: $log" | Tee-Object -FilePath $log -Append
