#!/usr/bin/env python3
"""
FPGA Placement HPWL Visualizer
Plots per-net HPWL for the initial vs final placement, plus a cross-case summary
(HPWL and CC final vs initial, and the runtime of each case from result/<case>_trace.csv).
The congestion (CC) map is drawn separately by `plot_placement.py --mode cc`.
Metrics come from PlacementMetrics in plot_placement.py, which follows src/Solver.cpp exactly.
"""

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from plot_placement import (FPGAPlacementParser, PlacementMetrics, style_axes,
                            COLOR_INITIAL, COLOR_FINAL, TEXT_PRIMARY, TEXT_SECONDARY, GRID_COLOR)

COLOR_RUNTIME = '#8c8b85'  # neutral gray: runtime is not a placement metric


def load_case(input_file, output_file):
    """Return (initial, final) PlacementMetrics for one testcase"""
    init_file = f"{Path(output_file).with_suffix('')}_init.txt"
    if not Path(init_file).exists():
        print(f"Error: initial placement file not found at {init_file}")
        sys.exit(1)
    initial = PlacementMetrics(FPGAPlacementParser(input_file, init_file))
    final = PlacementMetrics(FPGAPlacementParser(input_file, output_file))
    return initial, final


def draw_net_scatter(ax, initial, final):
    """Each net is a point: initial HPWL vs final HPWL; below the diagonal = got shorter"""
    names = list(initial.net_hpwl.keys())
    hi = np.array([initial.net_hpwl[n] for n in names])
    hf = np.array([final.net_hpwl[n] for n in names])
    rng = np.random.default_rng(0)  # small jitter so nets with identical integer HPWL don't hide each other
    jitter = lambda n: rng.uniform(-0.3, 0.3, n)
    shorter, longer = hf < hi, hf > hi
    same = ~(shorter | longer)

    lim = max(hi.max(), hf.max()) * 1.04
    ax.plot([0, lim], [0, lim], color=TEXT_SECONDARY, linewidth=1, linestyle='--', zorder=1)
    for mask, color, label in ((shorter, COLOR_FINAL, 'shorter'),
                               (same, '#a3a29c', 'unchanged'),
                               (longer, COLOR_INITIAL, 'longer')):
        ax.scatter(hi[mask] + jitter(mask.sum()), hf[mask] + jitter(mask.sum()), s=10, color=color,
                   alpha=0.6, linewidths=0, zorder=2,
                   label=f"{label}: {mask.sum()} nets ({mask.mean():.0%})")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_aspect('equal')
    ax.set_title('Per-net HPWL: initial vs final', fontsize=12, color=TEXT_PRIMARY, loc='left')
    ax.set_xlabel('Initial net HPWL')
    ax.set_ylabel('Final net HPWL')
    ax.grid(True, color=GRID_COLOR, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9, frameon=False, loc='upper left', markerscale=1.5,
              title='below y = x: net got shorter', title_fontsize=9, alignment='left')
    style_axes(ax)


def draw_sorted_hpwl(ax, initial, final):
    hi = np.sort(np.array(list(initial.net_hpwl.values())))[::-1]
    hf = np.sort(np.array(list(final.net_hpwl.values())))[::-1]
    rank = np.arange(1, len(hi) + 1)
    ax.fill_between(rank, hf, hi, color=COLOR_INITIAL, alpha=0.15, linewidth=0)
    ax.plot(rank, hi, color=COLOR_INITIAL, linewidth=2, label=f"Initial  Σ = {initial.hpwl:,.0f}")
    ax.plot(rank, hf, color=COLOR_FINAL, linewidth=2, label=f"Final    Σ = {final.hpwl:,.0f}")
    reduction = 1 - final.hpwl / initial.hpwl
    ax.text(0.97, 0.60, f"Shaded area = HPWL saved\n−{reduction:.1%}", transform=ax.transAxes,
            ha='right', va='top', fontsize=10, color=TEXT_PRIMARY)
    ax.set_title('Per-net HPWL, sorted (area = total HPWL)', fontsize=12, color=TEXT_PRIMARY, loc='left')
    ax.set_xlabel('Net rank (longest first)')
    ax.set_ylabel('Net HPWL')
    ax.set_xlim(1, len(rank))
    ax.set_ylim(bottom=0)
    ax.grid(True, axis='y', color=GRID_COLOR, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(fontsize=9, frameon=False, loc='upper right')
    style_axes(ax)


def plot_case(case_name, initial, final, save_to):
    fig = plt.figure(figsize=(18, 7.5), layout='constrained')
    axd = fig.subplot_mosaic([['scatter', 'sorted']], width_ratios=[1, 1.6])
    fig.patch.set_facecolor('white')

    draw_net_scatter(axd['scatter'], initial, final)
    draw_sorted_hpwl(axd['sorted'], initial, final)

    fig.suptitle(f"{case_name}: HPWL {initial.hpwl:,.0f} → {final.hpwl:,.0f} "
                 f"(−{1 - final.hpwl / initial.hpwl:.1%})",
                 fontsize=15, fontweight='bold', color=TEXT_PRIMARY, x=0.01, ha='left')

    fig.savefig(save_to, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Plot saved to {save_to}")


def load_runtime(output_file):
    """CPU time of the whole run in seconds, from the last row of <output>_trace.csv (None if no trace)"""
    trace = Path(f"{Path(output_file).with_suffix('')}_trace.csv")
    if not trace.exists():
        return None
    last = trace.read_text().strip().splitlines()[-1].split(',')
    return float(last[2])


def plot_summary(rows, save_to):
    """rows: list of (case_name, initial, final, runtime_seconds or None)"""
    names = [r[0] for r in rows]
    hpwl_ratio = [100 * f.hpwl / i.hpwl for _, i, f, _ in rows]
    cc_ratio = [100 * (f.cc - 1) / (i.cc - 1) for _, i, f, _ in rows]
    runtime = [r[3] for r in rows]
    have_runtime = all(t is not None for t in runtime)

    if have_runtime:
        fig, (ax, ax_t) = plt.subplots(1, 2, figsize=(17, 5.5), width_ratios=[1.6, 1], layout='constrained')
    else:
        fig, ax = plt.subplots(figsize=(11, 5.5))
    x = np.arange(len(names))
    width = 0.36
    bars_h = ax.bar(x - width / 2 - 0.01, hpwl_ratio, width, color=COLOR_INITIAL, label='HPWL')
    bars_c = ax.bar(x + width / 2 + 0.01, cc_ratio, width, color=COLOR_FINAL, label='Excess congestion (CC − 1)')
    for bars in (bars_h, bars_c):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1.5, f"{bar.get_height():.1f}%",
                    ha='center', va='bottom', fontsize=9, color=TEXT_PRIMARY)
    ax.axhline(100, color=TEXT_SECONDARY, linewidth=1, linestyle='--')
    ax.text(len(names) - 0.5, 101.5, 'initial = 100%', ha='right', va='bottom', fontsize=9, color=TEXT_SECONDARY)
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylim(0, 112)
    ax.set_ylabel('Final as % of initial (lower is better)')
    ax.set_title('Final vs initial placement across testcases', fontsize=13,
                 color=TEXT_PRIMARY, loc='left', fontweight='bold')
    ax.grid(True, axis='y', color=GRID_COLOR, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc='upper left', bbox_to_anchor=(0, 0.86))
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    style_axes(ax)

    if have_runtime:
        bars_t = ax_t.bar(x, runtime, 0.6, color=COLOR_RUNTIME, label='Runtime')
        for bar in bars_t:
            ax_t.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(runtime) * 0.015,
                      f"{bar.get_height():.0f} s", ha='center', va='bottom', fontsize=9, color=TEXT_PRIMARY)
        mean_t = np.mean(runtime)
        ax_t.axhline(mean_t, color=TEXT_SECONDARY, linewidth=1, linestyle='--')
        ax_t.text(len(names) - 0.5, mean_t + max(runtime) * 0.015, f'mean = {mean_t:.0f} s',
                  ha='right', va='bottom', fontsize=9, color=TEXT_SECONDARY)
        ax_t.set_xticks(x)
        ax_t.set_xticklabels(names)
        ax_t.set_ylim(0, max(runtime) * 1.12)
        ax_t.set_ylabel('CPU time of the whole run (s)')
        ax_t.set_title('Runtime across testcases', fontsize=13, color=TEXT_PRIMARY, loc='left', fontweight='bold')
        ax_t.grid(True, axis='y', color=GRID_COLOR, linewidth=0.6)
        ax_t.set_axisbelow(True)
        for spine in ('top', 'right'):
            ax_t.spines[spine].set_visible(False)
        style_axes(ax_t)

    fig.savefig(save_to, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Summary saved to {save_to}")


def print_metrics(case_name, initial, final):
    print(f"{case_name:>10}: HPWL {initial.hpwl:>10.1f} -> {final.hpwl:>10.1f}   "
          f"CC {initial.cc:.6f} -> {final.cc:.6f}")


def main():
    parser_args = argparse.ArgumentParser(
        description='Plot per-net HPWL of the initial vs final placement',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # One testcase -> plot/alu4_hpwl.png
  python plot_metrics.py testcases/alu4.txt result/alu4.out --save plot/

  # Every result/*.out -> plot/<case>_hpwl.png and plot/summary.png
  python plot_metrics.py --all --save plot/
        ''')
    parser_args.add_argument('input', nargs='?', help='Input testcase file')
    parser_args.add_argument('output', nargs='?', help='Output placement file')
    parser_args.add_argument('--all', action='store_true',
                             help='Process every result/*.out and also write summary.png')
    parser_args.add_argument('--save', default='plot/', help='Output directory (default: plot/)')
    args = parser_args.parse_args()

    save_dir = Path(args.save)
    save_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        cases = []
        # public test cases first, then the hidden ones
        for output_file in sorted(Path('result').glob('*.out'), key=lambda f: (f.stem.startswith('hidden'), f.stem)):
            case_name = output_file.stem
            input_file = Path('testcases') / f"{case_name}.txt"
            if not input_file.exists():
                print(f"Skipping {case_name}: input file not found ({input_file})")
                continue
            cases.append((case_name, str(input_file), str(output_file)))
    elif args.input and args.output:
        cases = [(Path(args.output).stem, args.input, args.output)]
    else:
        parser_args.error('give INPUT and OUTPUT, or --all')

    rows = []
    for case_name, input_file, output_file in cases:
        initial, final = load_case(input_file, output_file)
        print_metrics(case_name, initial, final)
        plot_case(case_name, initial, final, save_dir / f"{case_name}_hpwl.png")
        rows.append((case_name, initial, final, load_runtime(output_file)))

    if args.all and rows:
        plot_summary(rows, save_dir / 'summary.png')


if __name__ == '__main__':
    main()
