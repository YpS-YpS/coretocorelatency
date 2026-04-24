"""
Side-by-side comparison of multiple core-to-core-latency CSVs.

Shares one color scale across all panels so noise/structure is visually
comparable between runs. Reuses the repo-notebook load_data semantics.

Usage:
    py tools/compare_heatmaps.py data/a.csv data/b.csv data/c.csv \
        -o plots/compare.png --titles "quick,baseline,publication"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def load_data(filename):
    m = np.array(pd.read_csv(filename, header=None))
    return np.tril(m) + np.tril(m).transpose()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("csvs", nargs="+", type=Path, help="CSVs to compare")
    p.add_argument("-o", "--out", type=Path, required=True)
    p.add_argument("--titles", default="",
                   help="comma-delimited panel titles "
                        "(default: filenames)")
    p.add_argument("--shared-scale", action="store_true",
                   help="share vmin/vmax across panels (else per-panel)")
    p.add_argument("--dpi", type=int, default=130)
    p.add_argument("--annot", action="store_true",
                   help="draw per-cell numbers (only if cores <= 16)")
    args = p.parse_args()

    mats = [load_data(c) for c in args.csvs]
    shapes = {m.shape for m in mats}
    if len(shapes) != 1:
        print(f"matrix shapes differ: {shapes}", file=sys.stderr)
        return 2

    titles = (args.titles.split(",") if args.titles
              else [c.stem for c in args.csvs])
    if len(titles) != len(mats):
        print(f"--titles has {len(titles)}, need {len(mats)}", file=sys.stderr)
        return 2

    n_panels = len(mats)
    n_cores = mats[0].shape[0]
    panel_side = max(4.0, 0.3 * n_cores + 2.0)
    fig, axes = plt.subplots(
        1, n_panels,
        figsize=(panel_side * n_panels + 1.0, panel_side + 1.5),
        dpi=args.dpi,
    )
    if n_panels == 1:
        axes = [axes]

    if args.shared_scale:
        vmin = min(np.nanmin(m) for m in mats)
        vmax = max(np.nanmax(m) for m in mats)
    else:
        vmin = vmax = None

    im = None
    for ax, m, title in zip(axes, mats, titles):
        v_lo = vmin if vmin is not None else np.nanmin(m)
        v_hi = vmax if vmax is not None else np.nanmax(m)
        ax.imshow(np.full_like(m, 0.7), vmin=0, vmax=1, cmap="gray")
        im = ax.imshow(m, cmap=plt.get_cmap("viridis"), vmin=v_lo, vmax=v_hi)
        ax.set_title(
            f"{title}\n"
            f"min {v_lo:.0f}  median {np.nanmedian(m):.0f}  max {v_hi:.0f} ns",
            fontsize=10,
        )
        ax.set_xticks(np.arange(n_cores))
        ax.set_yticks(np.arange(n_cores))
        ax.set_xticklabels([f"{i+1}" for i in range(n_cores)], fontsize=7, rotation=90)
        ax.set_yticklabels([f"{i+1}" for i in range(n_cores)], fontsize=7)

        if args.annot and n_cores <= 16:
            black_at = (v_lo + 3 * v_hi) / 4
            for (i, j) in np.ndindex(m.shape):
                v = m[i, j]
                if np.isnan(v):
                    continue
                color = "w" if v < black_at else "k"
                ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                        color=color, fontsize=6)

    if args.shared_scale and im is not None:
        fig.colorbar(im, ax=axes, fraction=0.025, pad=0.02,
                     label="Latency (ns)")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=args.dpi, bbox_inches="tight", facecolor="w")
    plt.close(fig)
    print(f"wrote {args.out} ({n_panels} panels, {n_cores}x{n_cores})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
