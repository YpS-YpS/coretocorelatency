# Core-to-core latency benchmark + heatmap

One-click core-to-core latency measurement on Windows with automatic heatmap
generation. Wraps [nviennot/core-to-core-latency](https://github.com/nviennot/core-to-core-latency)
(prebuilt v1.0.0) and the repo's own Jupyter-notebook visualization, exposed
as a single `.bat` launcher.

Tested on a 16-logical-core Intel engineering sample; designed to scale to
28- and 52-core systems.

## Requirements

- Windows 10/11, x86_64
- Python 3.x installed from python.org (the `py` launcher on PATH)
- Python packages: `numpy pandas matplotlib scipy seaborn`
  - Install with: `py -m pip install -r requirements.txt`

No Rust toolchain required — the prebuilt `core-to-core-latency.exe` v1.0.0
ships in `bin\`.

## Quick start

```powershell
# One-time: install Python dependencies
py -m pip install -r requirements.txt

# Run with repo-recommended counts (5000 x 300), ~30s on 16 cores
.\start.bat

# Fast/noisy preview (1000 x 100), ~5s
.\start.bat quick

# Clean publication-quality data (30000 x 1000), ~3 min on 16 cores
.\start.bat publication

# Custom iteration and sample counts
.\start.bat 10000 500
```

Each run writes:

- `data\<preset>_<iters>x<samples>_<timestamp>.csv` — raw latency matrix
- `plots\<preset>_<iters>x<samples>_<timestamp>.png` — heatmap

The heatmap opens automatically in your default image viewer.

## What it measures

Two threads pin themselves to each pair of CPU cores and spin on an atomic
compare-and-swap (CAS) against one shared cache line. The ping-pong forces a
MESI coherency round-trip through the cache hierarchy / mesh fabric on every
iteration. Each matrix cell is the **mean over `<samples>` samples × `<iters>`
round-trips**, halved to report one-way latency in nanoseconds.

The heatmap reveals:

- **L1/L2-shared cache clusters** as tight dark blocks along the diagonal
  (~30-50 ns on modern x86)
- **NUMA / CCX / CCD boundaries** as sharp jumps in brightness
- **Mesh fabric geometry** as smoother gradients between far-apart cores
- **Socket boundaries** as the brightest (slowest) quadrants on dual-socket
  systems

## Runtime expectations

Scaling is roughly quadratic with logical core count (number of pairs =
`n*(n-1)/2`). Rough wall-clock time:

| Preset       | Counts         | 16-core | 28-core | 52-core |
|--------------|----------------|---------|---------|---------|
| `quick`      | 1000 × 100     | ~5 s    | ~2 s    | ~8 s    |
| `baseline`   | 5000 × 300     | ~30 s   | ~40 s   | ~2 min  |
| `publication`| 30000 × 1000   | ~3 min  | ~11 min | ~40 min |

`start.bat` prints an estimate before launching so you can decide whether to
commit.

## Choosing a preset

- **Linux or Windows without VBS/Hyper-V**: `baseline` is usually clean
  enough. RDTSC is typically available and gives sub-nanosecond resolution.
- **Windows 11 Enterprise / VBS enabled**: check the first line of the exe's
  output. If it says `Using RDTSC to measure time: false`, the tool falls
  back to `QueryPerformanceCounter` (~100 ns resolution). Prefer
  `publication` to push timer quantization below the signal — `quick` will
  produce a heatmap with only 3-4 discrete latency values.

## Advanced usage

### Plot a pre-existing CSV

```powershell
py tools\plot_heatmap.py data\run.csv -o plots\run.png `
   --title "My CPU" --iters 5000 --samples 300
```

### Compare multiple runs side-by-side

```powershell
py tools\compare_heatmaps.py data\quick.csv data\baseline.csv data\pub.csv `
   -o plots\compare.png --titles "quick,baseline,publication"
```

### Control per-cell number annotations

Numbers are shown by default at every core count. Override:

```powershell
# Suppress numbers above 24 cores (smaller image, colors only)
set ANNOT_MAX=24
.\start.bat

# Or directly via the Python CLI
py tools\plot_heatmap.py data\run.csv -o plot.png --annot-max 24
py tools\plot_heatmap.py data\run.csv -o plot.png --no-annot
```

### Programmatic sweep

Run the same target with multiple settings in one go:

```powershell
.\tools\run_sweep.ps1
```

Produces 3 heatmaps by default (quick / baseline / publication). Edit the
`-Configs` parameter for custom count pairs.

## File layout

```
.
├── README.md
├── requirements.txt
├── start.bat                      # one-click launcher
├── bin\
│   └── core-to-core-latency.exe   # prebuilt v1.0.0
├── tools\
│   ├── plot_heatmap.py            # CLI wrapper around repo's notebook
│   ├── compare_heatmaps.py        # side-by-side comparison
│   └── run_sweep.ps1              # multi-config sweep
├── data\                          # CSVs (created on first run)
└── plots\                         # PNGs (created on first run)
```

## Troubleshooting

### `py` not found
Install Python from python.org (the installer adds the `py` launcher to
PATH). Microsoft Store Python stubs don't include `py`.

### `ModuleNotFoundError: No module named 'numpy'`
Packages were installed into a different Python version than `py` currently
picks. Rerun `py -m pip install -r requirements.txt`.

### All cells read 0 ns (or very few discrete values)
Your build is on QPC and iteration count is too low. Use `publication` or
a custom run with `iters >= 5000`.

### `start.bat` not recognized when called from another directory
Always invoke as `.\start.bat` or a full path. It anchors all internal paths
on its own directory (`%~dp0`) so relocating the whole folder is safe.

## Credits

- Upstream benchmark: [nviennot/core-to-core-latency](https://github.com/nviennot/core-to-core-latency)
  (MIT)
- Visualization logic (`load_data`, `show_heapmap`) copied verbatim from the
  upstream `results/results.ipynb`.
