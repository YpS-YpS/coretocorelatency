# Run core-to-core-latency with multiple configs and plot each result.
#
# Usage:
#   .\tools\run_sweep.ps1                 # default 3-config sweep
#   .\tools\run_sweep.ps1 -Exe bin\core-to-core-latency.exe -OutDir data -PlotDir plots
#
# Each config is a pair: iterations_per_sample, num_samples.
# Defaults cover: quick/noisy, notebook-baseline, publication-quality.

param(
    [string]$Exe      = "bin\core-to-core-latency.exe",
    [string]$OutDir   = "data",
    [string]$PlotDir  = "plots",
    [string]$Title    = "Core-to-core latency",
    [int[][]]$Configs = @(
        @(1000,  100),
        @(5000,  300),
        @(30000, 1000)
    )
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Exe))     { throw "exe not found: $Exe" }
if (-not (Test-Path $OutDir))  { New-Item -ItemType Directory -Path $OutDir  | Out-Null }
if (-not (Test-Path $PlotDir)) { New-Item -ItemType Directory -Path $PlotDir | Out-Null }

foreach ($cfg in $Configs) {
    $iters = $cfg[0]
    $samps = $cfg[1]
    $tag   = "sweep_${iters}x${samps}"
    $csv   = Join-Path $OutDir "$tag.csv"
    $png   = Join-Path $PlotDir "$tag.png"

    Write-Host ""
    Write-Host "=== $tag ===" -ForegroundColor Cyan

    $start = Get-Date
    # cmd /c preserves clean ASCII redirection; PowerShell's default encoding
    # is UTF-16 with BOM which breaks pandas.read_csv.
    cmd /c "$Exe $iters $samps --csv > `"$csv`""
    $elapsed = (Get-Date) - $start
    Write-Host ("  benchmark took {0:N1}s" -f $elapsed.TotalSeconds)

    py tools\plot_heatmap.py $csv -o $png --title "$Title ($iters x $samps)"
}

Write-Host ""
Write-Host "done. plots at $PlotDir\" -ForegroundColor Green
