# V3.4 engine analysis toolkit
#
#   .\run_v34_analysis.ps1 arch        architecture report  (no simulation, ~20 s)
#   .\run_v34_analysis.ps1 list        list existing recordings you can view right now
#   .\run_v34_analysis.ps1 view        open the interactive viewer on the newest recording
#   .\run_v34_analysis.ps1 record      record Castlewood H/9 base + f567 with 2-D fields (~5 min)
#   .\run_v34_analysis.ps1 sweep       law sweep on Castlewood H/9 (~30-60 min)
#   .\run_v34_analysis.ps1 all         arch, then record, then sweep
#
# Extra arguments are passed straight through to the python script, e.g.
#   .\run_v34_analysis.ps1 view  --run LaurelRun__H9__wedge_f6_hc --compare LaurelRun__H12__wedge_f6_hc
#   .\run_v34_analysis.ps1 sweep --case LaurelRun --grid 9 --grid2 12
#   .\run_v34_analysis.ps1 record --case LaurelRun --grids 9 12 --variants f56 f567

param(
    [Parameter(Position = 0)]
    [ValidateSet("arch", "list", "view", "record", "sweep", "all")]
    [string]$Task = "arch",

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Rest
)

$ErrorActionPreference = "Stop"

$Repo    = "D:\My Projects\Dam-Breach-Studio"
$PyDir   = Join-Path $Repo "python"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Stamp   = Get-Date -Format "yyyy-MM-dd_HHmmss"

if (-not (Test-Path $PyDir)) {
    Write-Host "ERROR: cannot find $PyDir" -ForegroundColor Red
    exit 1
}
Set-Location $PyDir

function Invoke-Step {
    param([string]$Name, [string]$Script, [string[]]$Args, [switch]$NoLog)

    $script_path = Join-Path "calibration" $Script
    if (-not (Test-Path $script_path)) {
        Write-Host "ERROR: missing $script_path" -ForegroundColor Red
        Write-Host "Save the analysis scripts into: $(Join-Path $PyDir 'calibration')" -ForegroundColor Yellow
        exit 1
    }

    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  $Name" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  $Script $($Args -join ' ')" -ForegroundColor DarkGray
    Write-Host ""

    $t0 = Get-Date
    if ($NoLog) {
        & python -u $script_path @Args
    } else {
        $log = Join-Path $Desktop "v34_$($Name.ToLower() -replace '[^a-z0-9]+','_')_$Stamp.log"
        & python -u $script_path @Args 2>&1 | Tee-Object -FilePath $log
        Write-Host ""
        Write-Host "  log: $log" -ForegroundColor DarkGray
    }
    $code = $LASTEXITCODE
    Write-Host ("  elapsed {0:hh\:mm\:ss}" -f ((Get-Date) - $t0)) -ForegroundColor DarkGray
    if ($code -ne 0) { Write-Host "  exited with code $code" -ForegroundColor Yellow }
    return $code
}

switch ($Task) {

    "arch" {
        $a = @("--grids", "6", "9", "12", "--desktop", $Desktop)
        if ($Rest) { $a = $Rest }
        Invoke-Step "Architecture report" "v34_architecture_report.py" $a | Out-Null
    }

    "list" {
        Invoke-Step "Available recordings" "v34_view.py" @("--list") -NoLog | Out-Null
    }

    "view" {
        # interactive matplotlib window: no Tee, it must keep the console attached
        $a = $Rest
        if (-not $a) {
            $recDir = Join-Path $Repo "runs\v34_record"
            $diagDir = Join-Path $Repo "runs\v34_diag_laurel"
            $newest = Get-ChildItem -Path @($recDir, $diagDir) -Filter *.npz -ErrorAction SilentlyContinue |
                      Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if (-not $newest) {
                Write-Host "No recordings found. Run:  .\run_v34_analysis.ps1 record" -ForegroundColor Yellow
                exit 1
            }
            $a = @("--run", $newest.BaseName)
            Write-Host "Newest recording: $($newest.BaseName)" -ForegroundColor DarkGray
        }
        Write-Host "Controls: drag the slider, left/right arrows step, page up/down jump 20, space plays." -ForegroundColor DarkGray
        Invoke-Step "Run viewer" "v34_view.py" $a -NoLog | Out-Null
    }

    "record" {
        $a = @("--case", "Castlewood", "--grids", "9", "--variants", "base", "f567",
               "--workers", "2", "--desktop", $Desktop)
        if ($Rest) { $a = $Rest + @("--desktop", $Desktop) }
        Invoke-Step "Recorder" "v34_record.py" $a | Out-Null
        Write-Host ""
        Write-Host "Now view it:  .\run_v34_analysis.ps1 view" -ForegroundColor Green
    }

    "sweep" {
        $a = @("--case", "Castlewood", "--grid", "9", "--workers", "6", "--desktop", $Desktop)
        if ($Rest) { $a = $Rest + @("--desktop", $Desktop) }
        Invoke-Step "Law sweep" "v34_law_sweep.py" $a | Out-Null
    }

    "all" {
        Invoke-Step "Architecture report" "v34_architecture_report.py" `
            @("--grids", "6", "9", "12", "--desktop", $Desktop) | Out-Null
        Invoke-Step "Recorder" "v34_record.py" `
            @("--case", "Castlewood", "--grids", "9", "--variants", "base", "f567",
              "--workers", "2", "--desktop", $Desktop) | Out-Null
        Invoke-Step "Law sweep" "v34_law_sweep.py" `
            @("--case", "Castlewood", "--grid", "9", "--workers", "6", "--desktop", $Desktop) | Out-Null
        Write-Host ""
        Write-Host "Done. View the run:  .\run_v34_analysis.ps1 view" -ForegroundColor Green
    }
}

Write-Host ""
