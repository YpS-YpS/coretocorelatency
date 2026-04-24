"""
CLI wrapper around the repo's results/results.ipynb visualization.

Uses the upstream `load_data` and `show_heapmap` functions verbatim (pulled
straight out of the notebook) so plots match the repo's published style.
Adds: batch-friendly CLI, output-to-file, optional per-cell annotation
toggle, optional axis label override.

Usage:
    py tools/plot_heatmap.py data/run.csv -o plots/run.png --title "My CPU"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless — no GUI needed for file output
import matplotlib.pyplot as plt


# --- Verbatim from results/results.ipynb (cells 0-1) ------------------------
# Only adaptations: (a) use plt.get_cmap (plt.cm.get_cmap is deprecated in
# matplotlib 3.9+), (b) accept a pre-opened Figure so the caller can save,
# (c) accept optional ytick labels for labelling by core ID instead of 1..N.

def load_data(filename):
    m = np.array(pd.read_csv(filename, header=None))
    return np.tril(m) + np.tril(m).transpose()


def show_heapmap(m, title=None, subtitle=None, vmin=None, vmax=None,
                 yticks=True, figsize=None, labels=None, annot=True):
    vmin = np.nanmin(m) if vmin is None else vmin
    vmax = np.nanmax(m) if vmax is None else vmax
    black_at = (vmin + 3 * vmax) / 4
    subtitle = "Core-to-core latency" if subtitle is None else subtitle

    isnan = np.isnan(m)

    plt.rcParams['xtick.bottom'] = plt.rcParams['xtick.labelbottom'] = False
    plt.rcParams['xtick.top'] = plt.rcParams['xtick.labeltop'] = True

    figsize = (np.array(m.shape) * 0.3 + np.array([6, 1])
               if figsize is None else figsize)
    fig, ax = plt.subplots(figsize=figsize, dpi=130)

    fig.patch.set_facecolor('w')

    plt.imshow(np.full_like(m, 0.7), vmin=0, vmax=1, cmap='gray')  # alpha base
    plt.imshow(m, cmap=plt.get_cmap('viridis'), vmin=vmin, vmax=vmax)

    fontsize = 9 if vmax >= 100 else 10

    if annot:
        for (i, j) in np.ndindex(m.shape):
            t = ("" if isnan[i, j]
                 else f"{m[i, j]:.1f}" if vmax < 10.0
                 else f"{m[i, j]:.0f}")
            c = "w" if m[i, j] < black_at else "k"
            plt.text(j, i, t, ha="center", va="center", color=c, fontsize=fontsize)

    xlabels = labels if labels is not None else [f"{i+1}" for i in range(m.shape[1])]
    ylabels = ([f"CPU {x}" for x in labels] if labels is not None
               else [f"CPU {i+1}" for i in range(m.shape[0])])
    plt.xticks(np.arange(m.shape[1]), labels=xlabels, fontsize=9)
    if yticks:
        plt.yticks(np.arange(m.shape[0]), labels=ylabels, fontsize=9)
    else:
        plt.yticks([])

    plt.tight_layout()
    plt.title(f"{title}\n"
              f"{subtitle}\n"
              f"Min={vmin:0.1f}ns Median={np.nanmedian(m):0.1f}ns Max={vmax:0.1f}ns",
              fontsize=11, linespacing=1.5)
    return fig


# --- CLI --------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("csv", type=Path, help="headerless NxN CSV from the tool")
    p.add_argument("-o", "--out", type=Path, required=True, help="output image path")
    p.add_argument("--title", default="", help="plot title")
    p.add_argument("--subtitle", default=None, help="override subtitle")
    p.add_argument("--labels", default="",
                   help="comma-delimited core IDs for axis ticks "
                        "(default: 1..N to match the notebook)")
    p.add_argument("--no-annot", action="store_true",
                   help="disable per-cell latency numbers unconditionally")
    p.add_argument("--annot-max", type=int, default=9999,
                   dest="annot_max",
                   help="auto-disable per-cell numbers above this core count "
                        "(default: 9999, i.e. always annotate). Lower it "
                        "(e.g. --annot-max 24) to suppress numbers on large "
                        "matrices. Ignored when --no-annot is set.")
    p.add_argument("--iters", type=int, default=None,
                   help="iterations per sample used in the benchmark "
                        "(flows into the explanatory caption)")
    p.add_argument("--samples", type=int, default=None,
                   help="samples used in the benchmark "
                        "(flows into the explanatory caption)")
    p.add_argument("--dpi", type=int, default=130, help="output DPI")
    args = p.parse_args()

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        return 2

    m = load_data(args.csv)
    title = args.title or args.csv.stem

    labels = None
    if args.labels:
        labels = [int(x) for x in args.labels.split(",")]
        if len(labels) != m.shape[0]:
            print(f"--labels has {len(labels)} entries; need {m.shape[0]}",
                  file=sys.stderr)
            return 2

    # Figure sizing scales with core count; keeps cells and per-cell numbers
    # readable from 4 cores up through 52+. Extra ~2" of height for the
    # 2-line caption. At n=52 this produces ~28x22" which is big but needed
    # to keep annotation font legible.
    n = m.shape[0]
    figsize = (max(12.0, n * 0.45 + 4.5), max(8.0, n * 0.38 + 3.0))

    # Per-cell numbers become illegible on large matrices (52x52 = 2704 cells).
    # --no-annot forces off; otherwise annotate only up to --annot-max cores.
    annot = (not args.no_annot) and (n <= args.annot_max)

    fig = show_heapmap(
        m,
        title=title,
        subtitle=args.subtitle,
        labels=labels,
        annot=annot,
        figsize=figsize,
    )

    # Explanatory footer — 2 lines telling a fresh reader what this plot IS.
    # Attached as the axes' xlabel so matplotlib's tight_layout handles
    # positioning without fighting (x tick labels are on top per the
    # notebook's rcParams, so bottom xlabel is free to use).
    line1 = "What: two threads spin-CAS on one shared cache line (MESI round-trip)."
    if args.iters and args.samples:
        total = args.iters * args.samples
        line2 = (f"Count: mean of {args.samples} x {args.iters} "
                 f"round-trips/pair, halved = 1-way ns.")
    else:
        line2 = "Count: mean of N samples x M round-trips/pair, halved = 1-way ns."
    fig.axes[0].set_xlabel(
        line1 + "\n" + line2,
        fontsize=9, color="#333333", labelpad=10,
    )
    fig.tight_layout()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=args.dpi, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"wrote {args.out} ({m.shape[0]}x{m.shape[1]}, "
          f"min={np.nanmin(m):.1f}ns max={np.nanmax(m):.1f}ns "
          f"median={np.nanmedian(m):.1f}ns)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
