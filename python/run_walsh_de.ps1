# Walsh S3 stage-3 widening sensitivity (diagnostic only; Walsh is excluded, nothing is scored, engine file unchanged).
# Both runs keep (c) headcut_min_slope = 0.1 on, so the lip is no longer the limit and widening is tested.
# Compare with runs\diag_walsh\WalshS3_H16_pilot0.37m_t900_c_hc0.1_*  (50 L/s at 320 s, width 1.08 m)
#   (d) near_bank_shear_factor 1.0 -> 1.5   (more shear on the banks)
#   (e) lateral_model critical_shear -> force_balance   (Ikeda-type bank erosion)
# One after the other on ONE core (the calibration re-run keeps the other five). About 20-25 min each.
# Usage:  powershell -ExecutionPolicy Bypass -File "D:\My Projects\Dam-Breach-Studio\python\run_walsh_de.ps1"
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$log = Join-Path ([Environment]::GetFolderPath("Desktop")) "walsh_de_$(Get-Date -Format yyyyMMdd_HHmm).txt"
$common = @("--grid", "16", "--t-end", "900", "--log-every", "10", "--pilot-channel", "--section-every", "30",
            "--max-wall", "5400", "--cfg", "headcut_min_slope=0.1")
$runs = @(
    @{ Name = "(d) headcut 0.1 + near_bank_shear_factor 1.5"; Args = $common + @("--cfg", "near_bank_shear_factor=1.5", "--suffix", "_t900_d_hc0.1_nb1.5") },
    @{ Name = "(e) headcut 0.1 + lateral_model force_balance"; Args = $common + @("--cfg", "lateral_model=force_balance", "--suffix", "_t900_e_hc0.1_fb") }
)
foreach ($r in $runs) {
    "`n===== $($r.Name)   started $(Get-Date -Format HH:mm:ss) =====" | Tee-Object -FilePath $log -Append
    python -u calibration\diag_walsh.py @($r.Args) 2>&1 | ForEach-Object { "$_" } | Tee-Object -FilePath $log -Append
}
"`nAll done $(Get-Date -Format HH:mm:ss). Log: $log" | Tee-Object -FilePath $log -Append
