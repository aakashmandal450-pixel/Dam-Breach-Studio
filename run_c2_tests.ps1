# C2 verification in the acceptance order of note 06 draft 2.1 (§12):
#   Stage A  V8, V9, V10, V11, V13   (linear checks)
#   Stage B  V5, V5b, V6, V7, V12, V16 (nonlinear, energy, consistency, cost)
#   Stage C  V14 = the full phase B suite with C2 switched on (ONEDIM_COUPLING=c2)
# Each stage writes its own log to the Desktop and prints progress live.
# Usage:  powershell -ExecutionPolicy Bypass -File .\run_c2_tests.ps1              (A, then B, then C)
#         powershell -ExecutionPolicy Bypass -File .\run_c2_tests.ps1 -Stages A    (one stage)
#         powershell -ExecutionPolicy Bypass -File .\run_c2_tests.ps1 -Stages A,B -C2Mode chain
param([string]$Stages = "A,B,C", [string]$C2Mode = "independent")
$Repo    = "D:\My Projects\Dam-Breach-Studio"
$Desktop = [Environment]::GetFolderPath("Desktop")
Set-Location (Join-Path $Repo "python")
$env:ONEDIM_C2_MODE = $C2Mode
foreach ($s in $Stages.Split(",")) {
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $Log = Join-Path $Desktop "onedim_c2_stage$($s)_$Stamp.log"
    if ($s -eq "C") {
        $env:ONEDIM_COUPLING = "c2"
        Write-Host "Stage C: full phase B suite with C2 (ONEDIM_COUPLING=c2, mode $C2Mode)"
        python -B -u -m onedim.verification.run_phase_b 2>&1 | Tee-Object -FilePath $Log
        Remove-Item Env:\ONEDIM_COUPLING
    } else {
        python -B -u -m onedim.verification.c2_tests --stage $s 2>&1 | Tee-Object -FilePath $Log
    }
    Write-Host "`nStage $s log written to $Log`n"
}
Remove-Item Env:\ONEDIM_C2_MODE
