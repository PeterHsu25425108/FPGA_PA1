#!/usr/bin/env python3
"""
SA Placement Animator
Animates the placement over the SA run, from the snapshots the placer writes when the environment
variable SA_SNAPSHOT_EVERY is set (see src/main.cpp):

  SA_SNAPSHOT_EVERY=1 ./placer testcases/hidden3.txt result/hidden3.out 1
  python3 animate_sa.py testcases/hidden3.txt result/hidden3_snap.bin --frames 400 \
      --save plot/hidden3_anim.gif --dpi 64

With --frames, the frames are spaced so that stretches where the picture visibly changes (the
scramble at the start of round 1, the clusters forming as it cools, and each restart) play in slow
motion; see pick_frames. With snapshots on, the placer also takes one every 500 iterations during the
first 50,000 iterations of round 1, where the scramble happens.

Each frame shows
  - left:   every block as a filled site, colored by the column it started in, so you can follow
            where blocks move (empty sites are light gray, IOs red)
  - middle: the coverage map U / mean(U) on one fixed color scale (1 = average congestion)
  - bottom: the cost HPWL / HPWL_init + CC / CC_init over the run, with the current point marked
The last frames hold on the best placement, read from the output file next to the snapshots.
"""

import argparse
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import FixedLocator, FormatStrFormatter, NullLocator
import numpy as np

from plot_placement import (FPGAPlacementParser, style_axes, COLOR_FINAL,
                            TEXT_PRIMARY, TEXT_SECONDARY, GRID_COLOR)

FRAME_HEAD = np.dtype([('round', '<i4'), ('iter', '<i8'), ('T', '<f8'),
                       ('HPWL', '<f8'), ('CC', '<f8'), ('R_limit', '<f8')])


def read_snapshots(path):
    """Return (C, R, header records, positions[frame, block, 2])"""
    raw = Path(path).read_bytes()
    n, C, R = np.frombuffer(raw, '<i4', 3)
    frame = np.dtype(FRAME_HEAD.descr + [('pos', '<i2', (int(n), 2))])
    frames = np.frombuffer(raw, frame, offset=12)
    return int(C), int(R), frames, frames['pos']  # int16, converted per frame to save memory


class CoverageMap:
    """Vectorized U map, following plot_placement.PlacementMetrics (and src/Solver.cpp)"""

    def __init__(self, parser, block_names):
        index = {name: i for i, name in enumerate(block_names)}
        self.C, self.R = int(parser.C), int(parser.R)
        blk, starts = [], []
        io_bounds = []  # per net: (x_min, x_max, y_min, y_max) over its IOs
        for terminals in parser.nets.values():
            starts.append(len(blk))
            xs, ys = [], []
            for t in terminals:
                if t in index:
                    blk.append(index[t])
                elif t in parser.ios:
                    xs.append(parser.ios[t][0])
                    ys.append(parser.ios[t][1])
            io_bounds.append((min(xs, default=np.inf), max(xs, default=-np.inf),
                              min(ys, default=np.inf), max(ys, default=-np.inf)))
        self.blk = np.array(blk)
        self.starts = np.array(starts)
        self.has_blocks = np.diff(np.append(self.starts, len(blk))) > 0
        self.io = np.array(io_bounds).T

    def compute(self, pos):
        x, y = pos[self.blk, 0].astype(float), pos[self.blk, 1].astype(float)
        nb = self.has_blocks
        st = self.starts[nb]
        x_min, x_max, y_min, y_max = (a.copy() for a in self.io)
        x_min[nb] = np.minimum(x_min[nb], np.minimum.reduceat(x, st))
        x_max[nb] = np.maximum(x_max[nb], np.maximum.reduceat(x, st) + 1)
        y_min[nb] = np.minimum(y_min[nb], np.minimum.reduceat(y, st))
        y_max[nb] = np.maximum(y_max[nb], np.maximum.reduceat(y, st) + 1)
        hpwl = float(((x_max - x_min) + (y_max - y_min)).sum())
        # cells x in [ceil(x_min), ceil(x_max)), clipped to the chip; summed with a 2D difference array
        xs = np.clip(np.ceil(x_min), 0, self.C).astype(int)
        xe = np.clip(np.ceil(x_max), 0, self.C).astype(int)
        ys = np.clip(np.ceil(y_min), 0, self.R).astype(int)
        ye = np.clip(np.ceil(y_max), 0, self.R).astype(int)
        ok = (xs < xe) & (ys < ye)
        xs, xe, ys, ye = xs[ok], xe[ok], ys[ok], ye[ok]
        D = np.zeros((self.C + 1, self.R + 1), dtype=np.int64)
        np.add.at(D, (xs, ys), 1)
        np.add.at(D, (xe, ys), -1)
        np.add.at(D, (xs, ye), -1)
        np.add.at(D, (xe, ye), 1)
        U = D.cumsum(0).cumsum(1)[:self.C, :self.R]
        return U, hpwl


def progress_distance(pos, C, R, tile=8):
    """Distance of each snapshot to the last one, on a coarse map that averages over tile x tile sites.

    Per tile, the map holds the mean starting column of its blocks (the color in the animation)
    and the fraction of occupied sites. Random reshuffling at high temperature averages out on this
    map, so the distance only moves where the picture visibly changes: the initial gradient breaking
    up, clusters forming, and each restart.
    """
    col = pos[0][:, 0].astype(float) / max(C - 1, 1)
    nx, ny = -(-C // tile), -(-R // tile)

    def coarse(p):
        t = (p[:, 0] // tile).astype(np.int64) * ny + p[:, 1] // tile
        total = np.bincount(t, weights=col, minlength=nx * ny)
        count = np.bincount(t, minlength=nx * ny)
        return np.concatenate([total / np.maximum(count, 1), count / tile ** 2])

    final = coarse(pos[-1])
    return np.array([np.abs(coarse(p) - final).sum() for p in pos])


def pick_frames(pos, head, C, R, n_frames, uniform_share, max_repeat, smooth=25):
    """Return the snapshot shown in each of n_frames frames, slowing down where the picture changes.

    Each interval between two snapshots gets a share of the frames:
      (1 - uniform_share) in proportion to its change in progress_distance (smoothed over `smooth`
      snapshots, minus the median change as a noise floor), and uniform_share in proportion to its
      iterations, so quiet stretches still move on. No snapshot is shown for more than max_repeat frames, and
      the frames above that cap go to the other intervals.
    """
    if n_frames <= 0:
        return np.arange(len(pos))
    d = progress_distance(pos, C, R)
    k = min(smooth, len(d))
    ds = np.convolve(np.pad(d, (k // 2, k - 1 - k // 2), mode='edge'), np.ones(k) / k, mode='valid')
    change = np.abs(np.diff(ds))
    change = np.maximum(change - np.median(change), 0)
    iters = np.diff(head['iter']).astype(float)
    w = (1 - uniform_share) * change / max(change.sum(), 1e-12) + uniform_share * iters / iters.sum()
    f = n_frames * w
    for _ in range(20):  # cap, and hand the excess to the intervals below the cap
        over = f > max_repeat
        excess = (f[over] - max_repeat).sum()
        if excess < 1e-9:
            break
        f[over] = max_repeat
        free = ~over
        f[free] += excess * f[free] / f[free].sum()
    bounds = np.cumsum(f)
    return np.minimum(np.searchsorted(bounds, np.arange(n_frames) + 0.5), len(f) - 1) + 1


def load_trace(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    return {k: np.array([float(r[k]) for r in rows]) for k in rows[0]}


def main():
    ap = argparse.ArgumentParser(description='Animate the placement over the SA run')
    ap.add_argument('input', help='Testcase input file')
    ap.add_argument('snapshots', help='<case>_snap.bin written by the placer')
    ap.add_argument('--save', required=True, help='Output GIF')
    ap.add_argument('--fps', type=int, default=12)
    ap.add_argument('--dpi', type=int, default=80)
    ap.add_argument('--hold', type=int, default=24, help='Frames to hold on the best placement')
    ap.add_argument('--hold-start', type=int, default=12, help='Frames to hold on the initial placement')
    ap.add_argument('--frames', type=int, default=0,
                    help='Number of SA frames, spaced to slow down where the placement visibly changes '
                         '(default: one frame per snapshot); best with SA_SNAPSHOT_EVERY=1')
    ap.add_argument('--uniform-share', type=float, default=0.15,
                    help='With --frames: share of the frames spread evenly over the iterations')
    ap.add_argument('--max-repeat', type=int, default=3,
                    help='With --frames: most frames one snapshot may be shown for')
    args = ap.parse_args()

    snap = Path(args.snapshots)
    base = snap.with_name(snap.name.replace('_snap.bin', ''))
    case = base.name
    parser = FPGAPlacementParser(args.input, f"{base}.out")
    names = list(parser.blocks.keys())  # input order, as in the snapshots
    best_pos = np.array([parser.blocks[n] for n in names], dtype=np.int64)

    C, R, head, pos = read_snapshots(snap)
    trace = load_trace(f"{base}_trace.csv")
    cover = CoverageMap(parser, names)

    frame_idx = pick_frames(pos, head, C, R, args.frames, args.uniform_share, args.max_repeat)
    U0, hpwl0 = cover.compute(pos[0].astype(np.int64))
    cc0 = U0.size * float((U0.astype(float) ** 2).sum()) / float(U0.sum()) ** 2
    cost = lambda h, c: h / hpwl0 + c / cc0
    trace_cost = cost(trace['HPWL'], trace['CC'])
    best_cost = cost(trace['best_HPWL'], trace['best_CC'])
    U_best, hpwl_best = cover.compute(best_pos)
    cc_best = U_best.size * float((U_best.astype(float) ** 2).sum()) / float(U_best.sum()) ** 2

    # identity color: the column each block started in
    color_val = pos[0][:, 0].astype(float) / max(C - 1, 1)
    cmap_blocks = plt.get_cmap('viridis')
    norm_U = TwoSlopeNorm(vmin=0.0, vcenter=1.0, vmax=max(2.0, (U0 / U0.mean()).max()))

    fig = plt.figure(figsize=(13, 8.2), layout='constrained')
    fig.patch.set_facecolor('white')
    axd = fig.subplot_mosaic([['blocks', 'cover'], ['cost', 'cost']], height_ratios=[2.6, 1])
    ax_b, ax_u, ax_c = axd['blocks'], axd['cover'], axd['cost']

    for ax in (ax_b, ax_u):
        ax.set_xlim(0, C)
        ax.set_ylim(0, R)
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([])
        style_axes(ax)
    ax_b.set_facecolor('#f6f5f1')
    cmap_blocks = cmap_blocks.with_extremes(bad='#f6f5f1')  # empty sites

    def block_grid(p):
        g = np.full((C, R), np.nan)
        g[p[:, 0], p[:, 1]] = color_val
        return g.T

    blocks_img = ax_b.imshow(block_grid(pos[0]), origin='lower', extent=(0, C, 0, R), cmap=cmap_blocks,
                             vmin=0, vmax=1, interpolation='nearest')
    ax_b.scatter([p[0] for p in parser.ios.values()], [p[1] for p in parser.ios.values()],
                 s=14, color='#d6453d', marker='D', linewidths=0, zorder=3, clip_on=False)
    ax_b.set_title('Blocks, colored by starting column (red: IOs)', fontsize=11,
                   color=TEXT_PRIMARY, loc='left')
    img = ax_u.imshow((U0 / U0.mean()).T, origin='lower', extent=(0, C, 0, R), cmap='RdBu_r',
                      norm=norm_U, interpolation='nearest')
    fig.colorbar(img, ax=ax_u, shrink=0.85, label='U / mean(U)')
    ax_u.set_title('Congestion map U / mean(U)', fontsize=11, color=TEXT_PRIMARY, loc='left')

    x = trace['iter'] / 1e6
    rounds = trace['round'].astype(int)
    for k in np.unique(rounds):
        xs = x[rounds == k]
        if k % 2 == 0:
            ax_c.axvspan(xs[0], xs[-1], color='#f1f0ec', zorder=0, linewidth=0)
        ax_c.text((xs[0] + xs[-1]) / 2, 0.96, f"Round {k}", transform=ax_c.get_xaxis_transform(),
                  ha='center', va='top', fontsize=9, color=TEXT_SECONDARY)
    ax_c.plot(x, trace_cost, color='#a3a29c', linewidth=1, label='current cost')
    ax_c.plot(x, best_cost, color=COLOR_FINAL, linewidth=1.6, label='best cost')
    (cursor_line,) = ax_c.plot([], [], color=TEXT_PRIMARY, linewidth=1, linestyle='--')
    (cursor,) = ax_c.plot([], [], 'o', color=TEXT_PRIMARY, markersize=5)
    ax_c.set_yscale('log')
    ax_c.set_ylim(min(best_cost.min(), trace_cost.min()) * 0.95, trace_cost.max() * 1.25)
    ax_c.yaxis.set_major_locator(FixedLocator([0.9, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]))
    ax_c.yaxis.set_major_formatter(FormatStrFormatter('%g'))
    ax_c.yaxis.set_minor_locator(NullLocator())
    ax_c.set_xlim(0, x[-1])
    ax_c.set_xlabel('Iteration (millions)')
    ax_c.set_ylabel('Cost (log)')
    ax_c.grid(True, axis='y', color=GRID_COLOR, linewidth=0.6)
    ax_c.legend(frameon=False, loc='upper right', bbox_to_anchor=(1, 0.86), fontsize=9)
    for spine in ('top', 'right'):
        ax_c.spines[spine].set_visible(False)
    style_axes(ax_c)
    title = fig.suptitle('', fontsize=14, fontweight='bold', color=TEXT_PRIMARY, x=0.01, ha='left')

    # frame list: hold on the initial placement, the chosen snapshots, then hold on the output
    sequence = [0] * args.hold_start + list(frame_idx) + [-1] * args.hold
    ylo, yhi = ax_c.get_ylim()

    def draw(k):
        i = sequence[k]
        if i >= 0:
            p, h = pos[i].astype(np.int64), head[i]
            U, _ = cover.compute(p)
            c = cost(h['HPWL'], h['CC'])
            xi = h['iter'] / 1e6
            title.set_text(f"{case}  ·  round {h['round']}  ·  T = {h['T']:,.4g}  ·  "
                           f"R_limit = {h['R_limit']:.0f}  ·  HPWL = {h['HPWL']:,.0f}  ·  "
                           f"CC = {h['CC']:.4f}  ·  cost = {c:.4f}")
        else:
            p, U, xi, c = best_pos, U_best, x[-1], cost(hpwl_best, cc_best)
            title.set_text(f"{case}  ·  output (best placement)  ·  HPWL = {hpwl_best:,.0f}  ·  "
                           f"CC = {cc_best:.4f}  ·  cost = {c:.4f}")
        blocks_img.set_data(block_grid(p))
        img.set_data((U / U.mean()).T)
        cursor_line.set_data([xi, xi], [ylo, yhi])
        cursor.set_data([xi], [c])
        return blocks_img, img, cursor, cursor_line, title

    anim = FuncAnimation(fig, draw, frames=len(sequence), blit=False)
    Path(args.save).parent.mkdir(parents=True, exist_ok=True)
    anim.save(args.save, writer=PillowWriter(fps=args.fps), dpi=args.dpi)
    plt.close(fig)
    print(f"Animation saved to {args.save} ({len(np.unique(frame_idx))} of {len(head)} snapshots, "
          f"{len(sequence)} frames, {len(sequence) / args.fps:.0f} s)")


if __name__ == '__main__':
    main()
