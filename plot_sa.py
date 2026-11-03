#!/usr/bin/env python3
"""
SA Run Visualizer
Plots how HPWL, CC, the cost function, the temperature and the acceptance rate evolve over the
iterations of simulated annealing, from the <case>_trace.csv written by the placer (SA_TRACE in main.cpp).

The trace has one row per temperature step (every 5000 iterations).

Cost function: SA_update.cpp accepts a move based on
    dCost = costScale * (dHPWL / HPWL_init + dCC / CC_init),   costScale = 100 * (round 1 T0)
which is the step of costScale * cost with cost = HPWL / HPWL_init + CC / CC_init (2 for the initial
placement). The cost panel plots this cost on a shifted log axis: heights follow log(cost - c0), where
c0 lies a little below the final result, and the ticks show the cost itself. This stretches the range
near the final result, so the small gains of the later rounds stay visible, while the whole run,
restart peaks included, still fits without clipping.
"""

import argparse
import csv
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from plot_placement import (style_axes, COLOR_INITIAL, COLOR_FINAL,
                            TEXT_PRIMARY, TEXT_SECONDARY, GRID_COLOR)

COLOR_BEST = TEXT_PRIMARY


def load_trace(trace_file):
    """Return a dict of numpy arrays, one per CSV column"""
    with open(trace_file) as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{trace_file} is empty")
    return {key: np.array([float(r[key]) for r in rows]) for key in rows[0]}


def shade_rounds(ax, trace, label=False):
    """Alternate a light band per SA round so restarts of the temperature are visible"""
    x = trace['iter'] / 1e6
    rounds = trace['round'].astype(int)
    for k in np.unique(rounds):
        xs = x[rounds == k]
        if k % 2 == 0:
            ax.axvspan(xs[0], xs[-1], color='#f1f0ec', zorder=0, linewidth=0)
        if label:
            ax.text((xs[0] + xs[-1]) / 2, 1.02, f"Round {k}", transform=ax.get_xaxis_transform(),
                    ha='center', va='bottom', fontsize=9, color=TEXT_SECONDARY)


def finish_axes(ax, ylabel):
    ax.set_ylabel(ylabel)
    ax.grid(True, axis='y', color=GRID_COLOR, linewidth=0.6)
    ax.set_axisbelow(True)
    for spine in ('top', 'right'):
        ax.spines[spine].set_visible(False)
    style_axes(ax)


def plot_trace(case_name, trace, save_to):
    x = trace['iter'] / 1e6
    hpwl0, cc0 = trace['HPWL'][0], trace['CC'][0]
    # cost = HPWL / HPWL_init + CC / CC_init (2 for the initial placement)
    def norm_cost(hpwl, cc):
        return hpwl / hpwl0 + cc / cc0
    cost = norm_cost(trace['HPWL'], trace['CC'])
    best_cost = norm_cost(trace['best_HPWL'], trace['best_CC'])
    # CC is bounded below by 1 (uniform coverage); its excess CC - 1 goes on a log axis, with a small
    # floor so that a (numerically) perfect placement does not disappear from the axis
    cc_excess = np.maximum(trace['CC'] - 1, 1e-6)
    best_cc_excess = np.maximum(trace['best_CC'] - 1, 1e-6)

    # Shifted log axis for the cost: c0 lies delta below the final result, with delta a quarter of
    # the range the later rounds work in (from the final result up to the result of round 1, or the
    # highest cost a round ends at). The current cost never goes below the best kept one, and that
    # never below the final result, so every point stays above c0.
    rounds = trace['round'].astype(int)
    round_ends = [np.flatnonzero(rounds == k)[-1] for k in np.unique(rounds)]
    final_cost = best_cost[-1]
    later_span = max([best_cost[round_ends[0]]] + [cost[i] for i in round_ends]) - final_cost
    delta = 0.25 * max(later_span, 0.002 * final_cost)
    c0 = final_cost - delta

    has_range = 'R_limit' in trace
    ratios = [1, 1, 1, 0.8, 0.8] + ([0.8] if has_range else [])
    fig, axes = plt.subplots(len(ratios), 1, figsize=(14, 3 * sum(ratios)), sharex=True,
                             layout='constrained', gridspec_kw={'height_ratios': ratios})
    for i, ax in enumerate(axes):
        shade_rounds(ax, trace, label=(i == 0))

    # HPWL
    ax = axes[0]
    ax.semilogy(x, trace['HPWL'], color=COLOR_INITIAL, linewidth=1.2, label='current')
    ax.semilogy(x, trace['best_HPWL'], color=COLOR_BEST, linewidth=2, label='best kept')
    ax.set_title(f"HPWL   {hpwl0:,.0f} → {trace['best_HPWL'][-1]:,.0f}   (log scale)", fontsize=12,
                 color=TEXT_PRIMARY, loc='left', pad=18)
    ax.legend(frameon=False, fontsize=9, loc='upper right')
    finish_axes(ax, 'HPWL (log)')

    # CC
    ax = axes[1]
    # CC is bounded below by 1 (uniform coverage), so plot the excess CC - 1 on a log axis
    ax.semilogy(x, cc_excess, color=COLOR_FINAL, linewidth=1.2, label='current')
    ax.semilogy(x, best_cc_excess, color=COLOR_BEST, linewidth=2, label='best kept')
    ax.set_title(f"Congestion cost CC   {cc0:.4f} → {trace['best_CC'][-1]:.4f}   "
                 f"(plotted as CC − 1, log scale; CC = 1 is uniform)", fontsize=12,
                 color=TEXT_PRIMARY, loc='left')
    ax.legend(frameon=False, fontsize=9, loc='upper right')
    finish_axes(ax, 'CC − 1 (log)')

    # Cost function
    ax = axes[2]
    ax.plot(x, cost, color='#6250d6', linewidth=1.2, label='current')
    ax.plot(x, best_cost, color=COLOR_BEST, linewidth=2, label='best kept')
    ax.set_yscale('function', functions=(lambda y: np.log(np.maximum(y - c0, 1e-12)),
                                         lambda z: np.exp(z) + c0))
    ax.set_ylim(c0 + 0.5 * delta, cost.max() * 1.03)
    # ticks: the final result, the result of round 1, and round numbers above
    ticks = {round(final_cost, 3), round(best_cost[round_ends[0]], 3)}
    ticks |= {t for t in (1.0, 1.5, 2.0) if final_cost + 2 * delta < t < cost.max() * 1.03}
    ax.set_yticks(sorted(ticks))
    ax.set_yticklabels([f"{t:.3f}" if t < 1 else f"{t:.1f}" for t in sorted(ticks)])
    ax.minorticks_off()
    ax.set_title(f"Cost = HPWL / HPWL₀ + CC / CC₀   2 → {final_cost:.4f}   "
                 f"(shifted log axis: height ∝ log(cost − {c0:.3f}))", fontsize=12,
                 color=TEXT_PRIMARY, loc='left')
    ax.legend(frameon=False, fontsize=9, loc='upper right')
    finish_axes(ax, 'Cost')

    # Temperature
    ax = axes[3]
    ax.semilogy(x, trace['T'], color=TEXT_PRIMARY, linewidth=1.5)
    t0_per_round = [trace['T0'][trace['round'] == k][0] for k in np.unique(trace['round'])]
    starts = ' → '.join(f"{t:,.0f}" for t in t0_per_round)
    ax.set_title(f"Temperature T   (round initial T: {starts})", fontsize=12,
                 color=TEXT_PRIMARY, loc='left')
    finish_axes(ax, 'T (log)')

    # Acceptance rate (drives the cooling rate in coolRate())
    ax = axes[4]
    ax.plot(x[1:], trace['accept_rate'][1:] * 100, color='#1baf7a', linewidth=1.2)
    for level in (15, 80, 95):
        ax.axhline(level, color=TEXT_SECONDARY, linewidth=0.8, linestyle=':')
        ax.text(x[-1], level, f"{level}%", ha='right', va='bottom', fontsize=8, color=TEXT_SECONDARY)
    ax.set_ylim(0, 100)
    ax.set_title('Acceptance rate per temperature step   (thresholds of coolRate())', fontsize=12,
                 color=TEXT_PRIMARY, loc='left')
    finish_axes(ax, 'Accepted (%)')

    # Move range of range-limited moves
    if has_range:
        ax = axes[5]
        ax.plot(x, trace['R_limit'], color='#eda100', linewidth=1.5)
        ax.set_ylim(bottom=0)
        ax.set_title('Move range R_limit   (target within ±R_limit of the block)', fontsize=12,
                     color=TEXT_PRIMARY, loc='left')
        finish_axes(ax, 'R_limit (cells)')

    axes[-1].set_xlabel('Iteration (millions)')
    axes[-1].set_xlim(x[0], x[-1])

    fig.suptitle(f"{case_name}: simulated annealing run   ({trace['iter'][-1] / 1e6:.1f}M iterations, "
                 f"{trace['time'][-1]:.0f} s)", fontsize=15, fontweight='bold', color=TEXT_PRIMARY,
                 x=0.01, ha='left')

    Path(save_to).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(save_to, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"Plot saved to {save_to}")


def main():
    parser_args = argparse.ArgumentParser(
        description='Plot HPWL, CC, cost, temperature and acceptance rate over the SA iterations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # One trace -> plot/alu4_sa.png
  python plot_sa.py result/alu4_trace.csv --save plot/

  # Every *_trace.csv in a directory
  python plot_sa.py result/*_trace.csv --save plot/

  # A trace of another version, with its own name
  python plot_sa.py bench/abl_v2/clma_2_s1_trace.csv --name clma_2_before --save docs/figures/results/
        ''')
    parser_args.add_argument('traces', nargs='+', help='<case>_trace.csv file(s) written by the placer')
    parser_args.add_argument('--save', default='plot/', help='Output directory (default: plot/)')
    parser_args.add_argument('--name', help='Name used in the title and as <name>_sa.png (one trace only)')
    args = parser_args.parse_args()

    if args.name and len(args.traces) != 1:
        parser_args.error('--name needs exactly one trace')
    for trace_file in args.traces:
        case_name = args.name or Path(trace_file).name.replace('_trace.csv', '')
        plot_trace(case_name, load_trace(trace_file), Path(args.save) / f"{case_name}_sa.png")


if __name__ == '__main__':
    main()
