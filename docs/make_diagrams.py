#!/usr/bin/env python3
"""
Explanatory diagrams for README / slides. Writes PNG and SVG into docs/figures/.
Usage: python3 docs/make_diagrams.py
"""

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Rectangle, Ellipse, FancyArrowPatch

OUT_DIR = Path(__file__).resolve().parent / 'figures'

INK = '#2b2b29'
MUTED = '#8f8e88'
GRID = '#dedcd6'
BLOCK_FILL = '#dbe7f7'
BLOCK_EDGE = '#2a78d6'
MOVED = '#eb6834'
ANCHOR = '#1baf7a'
NET1 = '#6250d6'
NET2 = '#eb6834'
TERMINAL_FILL = '#e8f0fb'
DECISION_FILL = '#fdf1ea'
POS = '#e34948'
NEG = '#2a78d6'

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 13, 'svg.fonttype': 'none'})


def save(fig, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ('png', 'svg'):
        fig.savefig(OUT_DIR / f"{name}.{ext}", dpi=200, bbox_inches='tight', pad_inches=0.15,
                    facecolor='white')
    plt.close(fig)
    print(f"Saved {OUT_DIR / name}.png/.svg")


def arrow(ax, points, label=None, label_at=0, label_offset=(0.1, 0.1)):
    """Orthogonal connector through points, arrowhead at the last point"""
    xs, ys = zip(*points)
    ax.plot(xs[:-1], ys[:-1], color=INK, linewidth=1.4, solid_capstyle='butt', zorder=1)
    ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle='-|>', mutation_scale=16,
                                 color=INK, linewidth=1.4, shrinkA=0, shrinkB=0, zorder=1))
    if label:
        x, y = points[label_at]
        ax.text(x + label_offset[0], y + label_offset[1], label, fontsize=11, color='#52514e',
                ha='left', va='bottom')


# ---------------------------------------------------------------------------
# 1. Overall flow chart
# ---------------------------------------------------------------------------
BOX_W, BOX_H = 3.2, 0.55
DIA_W, DIA_H = 2.0, 0.9


def process(ax, x, y, text, w=BOX_W):
    ax.add_patch(Rectangle((x - w / 2, y - BOX_H / 2), w, BOX_H, facecolor='white',
                           edgecolor=INK, linewidth=1.4, zorder=2))
    ax.text(x, y, text, ha='center', va='center', zorder=3)


def terminal(ax, x, y, text):
    ax.add_patch(FancyBboxPatch((x - 0.9, y - BOX_H / 2), 1.8, BOX_H,
                                boxstyle='round,pad=0,rounding_size=0.275', facecolor=TERMINAL_FILL,
                                edgecolor=INK, linewidth=1.4, zorder=2))
    ax.text(x, y, text, ha='center', va='center', zorder=3)


def data(ax, x, y, text, w=BOX_W):
    s = 0.22
    ax.add_patch(Polygon([(x - w / 2 + s, y + BOX_H / 2), (x + w / 2 + s, y + BOX_H / 2),
                          (x + w / 2 - s, y - BOX_H / 2), (x - w / 2 - s, y - BOX_H / 2)],
                         facecolor='white', edgecolor=INK, linewidth=1.4, zorder=2))
    ax.text(x, y, text, ha='center', va='center', zorder=3)


def decision(ax, x, y, text, w=DIA_W):
    ax.add_patch(Polygon([(x, y + DIA_H / 2), (x + w / 2, y), (x, y - DIA_H / 2), (x - w / 2, y)],
                         facecolor=DECISION_FILL, edgecolor=INK, linewidth=1.4, zorder=2))
    ax.text(x, y, text, ha='center', va='center', zorder=3)


def flow_chart():
    fig, ax = plt.subplots(figsize=(6.4, 11))
    h, d = BOX_H / 2, DIA_H / 2
    y = {'start': 0, 'read': -1, 'init': -2, 'perturb': -3, 'eval': -4, 'accept': -5.1,
         'branch': -6.3, 'cool': -7.4, 'frozen': -8.55, 'last': -9.9, 'write': -11.1, 'end': -12.1}
    xc, xl, xr, x_reheat = 0, -1.5, 1.5, 3.3

    terminal(ax, xc, y['start'], 'Start')
    data(ax, xc, y['read'], 'Read netlist')
    process(ax, xc, y['init'], 'Initial placement')
    process(ax, xc, y['perturb'], 'Move / swap a block')
    process(ax, xc, y['eval'], 'Compute ΔCost')
    decision(ax, xc, y['accept'], 'Accept?')
    process(ax, xl, y['branch'], 'Commit', w=1.6)
    process(ax, xr, y['branch'], 'Undo', w=1.6)
    process(ax, xc, y['cool'], 'Update T')
    decision(ax, xc, y['frozen'], 'Frozen?')
    decision(ax, xc, y['last'], 'Last round?', w=2.3)
    process(ax, x_reheat, y['last'], 'Reheat', w=1.5)
    data(ax, xc, y['write'], 'Write best placement', w=3.6)
    terminal(ax, xc, y['end'], 'End')

    for a, b in (('start', 'read'), ('read', 'init'), ('init', 'perturb'), ('perturb', 'eval')):
        arrow(ax, [(xc, y[a] - h), (xc, y[b] + h)])
    arrow(ax, [(xc, y['eval'] - h), (xc, y['accept'] + d)])

    # Accept? -> Commit / Undo -> merge into Update T
    arrow(ax, [(xc - DIA_W / 2, y['accept']), (xl, y['accept']), (xl, y['branch'] + h)],
          label='Yes', label_at=1, label_offset=(-0.45, 0.05))
    arrow(ax, [(xc + DIA_W / 2, y['accept']), (xr, y['accept']), (xr, y['branch'] + h)],
          label='No', label_at=1, label_offset=(0.05, 0.05))
    merge = y['branch'] - h - 0.25
    ax.plot([xl, xl, xr, xr], [y['branch'] - h, merge, merge, y['branch'] - h], color=INK,
            linewidth=1.4, zorder=1)
    arrow(ax, [(xc, merge), (xc, y['cool'] + h)])
    arrow(ax, [(xc, y['cool'] - h), (xc, y['frozen'] + d)])

    # Frozen? No -> back to Move / swap
    x_loop = -2.5
    arrow(ax, [(xc - DIA_W / 2, y['frozen']), (x_loop, y['frozen']), (x_loop, y['perturb']),
               (xc - BOX_W / 2, y['perturb'])],
          label='No', label_at=0, label_offset=(-0.5, 0.05))
    arrow(ax, [(xc, y['frozen'] - d), (xc, y['last'] + d)],
          label='Yes', label_at=0, label_offset=(0.08, -0.32))

    # Last round? No -> Reheat -> back to Move / swap
    arrow(ax, [(xc + 2.3 / 2, y['last']), (x_reheat - 0.75, y['last'])],
          label='No', label_at=0, label_offset=(0.1, 0.05))
    arrow(ax, [(x_reheat, y['last'] + h), (x_reheat, y['perturb']), (xc + BOX_W / 2, y['perturb'])])
    arrow(ax, [(xc, y['last'] - d), (xc, y['write'] + h)],
          label='Yes', label_at=0, label_offset=(0.08, -0.32))
    arrow(ax, [(xc, y['write'] - h), (xc, y['end'] + h)])

    ax.set_xlim(-2.8, 4.2)
    ax.set_ylim(-12.6, 0.5)
    ax.set_aspect('equal')
    ax.axis('off')
    save(fig, 'flow')


# ---------------------------------------------------------------------------
# Grid helpers for the mechanism diagrams (cell (x, y) spans [x, x+1] x [y, y+1])
# ---------------------------------------------------------------------------
def grid(ax, cols, rows):
    for x in range(cols + 1):
        ax.plot([x, x], [0, rows], color=GRID, linewidth=0.8, zorder=0)
    for y in range(rows + 1):
        ax.plot([0, cols], [y, y], color=GRID, linewidth=0.8, zorder=0)
    ax.set_xlim(-0.6, cols + 0.6)
    ax.set_ylim(-0.6, rows + 0.6)
    ax.set_aspect('equal')
    ax.axis('off')


def block(ax, x, y, label=None, fill=BLOCK_FILL, edge=BLOCK_EDGE, ghost=False):
    ax.add_patch(FancyBboxPatch((x + 0.15, y + 0.15), 0.7, 0.7,
                                boxstyle='round,pad=0,rounding_size=0.1',
                                facecolor='none' if ghost else fill, edgecolor=edge,
                                linewidth=1.6, linestyle=(0, (3, 2)) if ghost else '-', zorder=3))
    if label:
        ax.text(x + 0.5, y + 0.5, label, ha='center', va='center', fontsize=13,
                fontweight='bold', color=INK, alpha=0.45 if ghost else 1, zorder=4)


def bbox(ax, x0, x1, y0, y1, color, dashed=False, inset=0.0, label=None, label_pos='tr'):
    ax.add_patch(Rectangle((x0 + inset, y0 + inset), x1 - x0 - 2 * inset, y1 - y0 - 2 * inset,
                           facecolor='none', edgecolor=color, linewidth=2.2,
                           linestyle=(0, (5, 3)) if dashed else '-', zorder=2))
    if label:
        positions = {'tr': (x1 - inset, y1 - inset + 0.12, 'right', 'bottom'),
                     'tl': (x0 + inset, y1 - inset + 0.12, 'left', 'bottom'),
                     'br': (x1 - inset, y0 + inset - 0.12, 'right', 'top'),
                     'bl': (x0 + inset, y0 + inset - 0.12, 'left', 'top')}
        x, y, ha, va = positions[label_pos]
        ax.text(x, y, label, ha=ha, va=va, fontsize=12, color=color, fontweight='bold')


def move(ax, src, dst, color=MOVED, style='-|>'):
    ax.add_patch(FancyArrowPatch((src[0] + 0.5, src[1] + 0.5), (dst[0] + 0.5, dst[1] + 0.5),
                                 arrowstyle=style, mutation_scale=18, color=color, linewidth=2,
                                 shrinkA=14, shrinkB=14, connectionstyle='arc3,rad=-0.25', zorder=5))


# ---------------------------------------------------------------------------
# 2. Net bounding box incremental update (block moves outside the box)
# ---------------------------------------------------------------------------
def bbox_update():
    fig, ax = plt.subplots(figsize=(6.5, 4.8))
    grid(ax, 8, 6)
    for x, y in ((1, 1), (3, 4)):
        block(ax, x, y)
    block(ax, 4, 2, ghost=True, edge=MOVED)
    block(ax, 6, 3, fill='#fbe1d6', edge=MOVED)
    move(ax, (4, 2), (6, 3))
    bbox(ax, 1, 5, 1, 5, MUTED, dashed=True, inset=0.06, label='old bbox', label_pos='tl')
    bbox(ax, 1, 7, 1, 5, MOVED, inset=-0.06, label='new bbox', label_pos='br')
    save(fig, 'bbox_update')


# ---------------------------------------------------------------------------
# 3. Anchor check: (a) another block still on the boundary, (b) no anchor -> box shrinks
# ---------------------------------------------------------------------------
def anchor_check():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))

    ax = axes[0]
    grid(ax, 7, 6)
    for x, y in ((1, 1), (2, 4)):
        block(ax, x, y)
    block(ax, 5, 3, fill='#d3f0e5', edge=ANCHOR)
    ax.text(6.15, 3.5, 'anchor', ha='left', va='center', fontsize=12, color=ANCHOR, fontweight='bold')
    block(ax, 5, 1, ghost=True, edge=MOVED)
    block(ax, 3, 2, fill='#fbe1d6', edge=MOVED)
    move(ax, (5, 1), (3, 2))
    bbox(ax, 1, 6, 1, 5, INK, inset=-0.06, label='bbox', label_pos='tl')

    ax = axes[1]
    grid(ax, 7, 6)
    for x, y in ((1, 1), (2, 4), (3, 3)):
        block(ax, x, y)
    block(ax, 5, 1, ghost=True, edge=MOVED)
    block(ax, 3, 2, fill='#fbe1d6', edge=MOVED)
    move(ax, (5, 1), (3, 2))
    bbox(ax, 1, 6, 1, 5, MUTED, dashed=True, inset=-0.06, label='old bbox', label_pos='tr')
    bbox(ax, 1, 4, 1, 5, MOVED, inset=0.06, label='new bbox', label_pos='bl')

    fig.subplots_adjust(wspace=0.15)
    save(fig, 'anchor_check')


# ---------------------------------------------------------------------------
# 4. Affected net filtering on a swap: a net holding both A and B keeps its box
# ---------------------------------------------------------------------------
def net_filter():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    A, B, C, D = (1, 3), (4, 1), (3, 4), (0, 4)

    for ax, (a, b) in zip(axes, ((A, B), (B, A))):
        grid(ax, 6, 6)
        block(ax, *C)
        block(ax, *D)
        block(ax, *a, label='A')
        block(ax, *b, label='B')
        net2 = [a, D]
        x0 = min(p[0] for p in net2); x1 = max(p[0] for p in net2) + 1
        y0 = min(p[1] for p in net2); y1 = max(p[1] for p in net2) + 1
        bbox(ax, 1, 5, 1, 5, NET1, inset=-0.06, label='net 1', label_pos='br')
        bbox(ax, x0, x1, y0, y1, NET2, inset=0.08, label='net 2', label_pos='tl')

    move(axes[0], A, B, color=INK, style='<|-|>')
    fig.subplots_adjust(wspace=0.15)
    save(fig, 'net_filter')


# ---------------------------------------------------------------------------
# 5. Incremental update of the coverage map U: -1 on the old box, +1 on the new box
# ---------------------------------------------------------------------------
def u_update():
    cols, rows = 6, 5
    U = [[1, 2, 2, 1, 0, 0],
         [2, 3, 4, 3, 1, 0],
         [2, 4, 5, 4, 2, 1],
         [1, 3, 3, 3, 2, 1],
         [0, 1, 2, 2, 1, 0]]  # U[row][col], row 0 = top
    old = (1, 4, 1, 3)  # x0, x1, y0, y1 in cell units (row index counted from the bottom)
    new = (2, 5, 1, 4)

    def inside(x, y, box):
        return box[0] <= x < box[1] and box[2] <= y < box[3]

    dU = [[(1 if inside(x, rows - 1 - r, new) else 0) - (1 if inside(x, rows - 1 - r, old) else 0)
           for x in range(cols)] for r in range(rows)]
    U2 = [[U[r][x] + dU[r][x] for x in range(cols)] for r in range(rows)]

    fig, axes = plt.subplots(1, 3, figsize=(14, 3.9))
    cmap = matplotlib.colormaps['Oranges']

    def heat(ax, values, name):
        grid(ax, cols, rows)
        for r in range(rows):
            for x in range(cols):
                v = values[r][x]
                y = rows - 1 - r
                ax.add_patch(Rectangle((x, y), 1, 1, facecolor=cmap(0.08 + v / 8), edgecolor=GRID,
                                       linewidth=0.8, zorder=1))
                ax.text(x + 0.5, y + 0.5, str(v), ha='center', va='center', fontsize=13,
                        color='white' if v >= 5 else INK, zorder=2)
        ax.text(cols / 2, -0.35, name, ha='center', va='top', fontsize=15, fontweight='bold', color=INK)

    heat(axes[0], U, 'U')

    ax = axes[1]
    grid(ax, cols, rows)
    for r in range(rows):
        for x in range(cols):
            v = dU[r][x]
            if v == 0:
                continue
            y = rows - 1 - r
            ax.add_patch(Rectangle((x, y), 1, 1, facecolor='#fbe0df' if v > 0 else '#dce9f9',
                                   edgecolor=GRID, linewidth=0.8, zorder=1))
            ax.text(x + 0.5, y + 0.5, f"{v:+d}", ha='center', va='center', fontsize=13,
                    fontweight='bold', color=POS if v > 0 else NEG, zorder=2)
    bbox(ax, old[0], old[1], old[2], old[3], NEG, dashed=True, inset=0.06,
         label='old bbox', label_pos='bl')
    bbox(ax, new[0], new[1], new[2], new[3], POS, inset=-0.06, label='new bbox', label_pos='tr')
    ax.text(cols / 2, -0.35, 'ΔU', ha='center', va='top', fontsize=15, fontweight='bold', color=INK)

    heat(axes[2], U2, "U'")

    for x_fig, symbol in ((0.365, '+'), (0.645, '=')):
        fig.text(x_fig, 0.55, symbol, ha='center', va='center', fontsize=30, color=INK)
    fig.subplots_adjust(wspace=0.3)
    save(fig, 'u_update')


if __name__ == '__main__':
    flow_chart()
    bbox_update()
    anchor_check()
    net_filter()
    u_update()
