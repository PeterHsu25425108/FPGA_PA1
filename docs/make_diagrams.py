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

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 13, 'svg.fonttype': 'none',
                     'svg.hashsalt': 'fpga-pa1'})  # fixed ids so unchanged figures stay byte-identical


def save(fig, name):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ('png', 'svg'):
        fig.savefig(OUT_DIR / f"{name}.{ext}", dpi=200, bbox_inches='tight', pad_inches=0.15,
                    facecolor='white', metadata={'Date': None} if ext == 'svg' else None)
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
# 1b. Flow chart of the final version (guided moves, best by cost, restarts)
# ---------------------------------------------------------------------------
def flow_chart_final():
    fig, ax = plt.subplots(figsize=(8.6, 15.5))
    h, d = BOX_H / 2, DIA_H / 2
    y = {'start': 0, 'read': -1, 'init': -2, 'set': -3, 'join': -3.65, 'guided': -4.55,
         'move': -5.75, 'eval': -6.85, 'accept': -7.95, 'branch': -9.15, 'best': -10.4,
         'save': -11.6, 'merge': -12.2, 'update': -12.7, 'stalled': -13.85, 'last': -15.25,
         'write': -16.45, 'end': -17.45}
    xc, xl, xr = 0, -2.5, 2.4
    w_opt, w_rng, w_small = 4.0, 3.2, 1.8
    w_best, w_stall, w_last = 2.6, 3.8, 2.4
    x_loop_l, x_loop_r = -5.0, 4.6

    terminal(ax, xc, y['start'], 'Start')
    data(ax, xc, y['read'], 'Read netlist')
    process(ax, xc, y['init'], 'Initial placement')
    process(ax, xc, y['set'], 'Set T, R_limit')
    decision(ax, xc, y['guided'], 'Guided?')
    process(ax, xl, y['move'], 'Move into optimal region', w=w_opt)
    process(ax, xr, y['move'], 'Move within R_limit', w=w_rng)
    process(ax, xc, y['eval'], 'Compute ΔCost')
    decision(ax, xc, y['accept'], 'Accept?')
    process(ax, xl, y['branch'], 'Commit', w=w_small)
    process(ax, xr, y['branch'], 'Undo', w=w_small)
    decision(ax, xl, y['best'], 'Cost < best?', w=w_best)
    process(ax, xl, y['save'], 'Save best', w=w_small)
    process(ax, xc, y['update'], 'Update T, R_limit')
    decision(ax, xc, y['stalled'], 'Stalled or frozen?', w=w_stall)
    decision(ax, xc, y['last'], 'Last round?', w=w_last)
    data(ax, xc, y['write'], 'Write best placement', w=3.6)
    terminal(ax, xc, y['end'], 'End')

    for a, b in (('start', 'read'), ('read', 'init'), ('init', 'set')):
        arrow(ax, [(xc, y[a] - h), (xc, y[b] + h)])
    arrow(ax, [(xc, y['set'] - h), (xc, y['guided'] + d)])

    # Guided? -> optimal region / R_limit window -> Compute delta cost
    arrow(ax, [(xc - DIA_W / 2, y['guided']), (xl, y['guided']), (xl, y['move'] + h)],
          label='Yes', label_at=1, label_offset=(-0.5, 0.05))
    arrow(ax, [(xc + DIA_W / 2, y['guided']), (xr, y['guided']), (xr, y['move'] + h)],
          label='No', label_at=1, label_offset=(0.05, 0.05))
    merge_move = y['move'] - h - 0.25
    ax.plot([xl, xl, xr, xr], [y['move'] - h, merge_move, merge_move, y['move'] - h], color=INK,
            linewidth=1.4, zorder=1)
    arrow(ax, [(xc, merge_move), (xc, y['eval'] + h)])
    arrow(ax, [(xc, y['eval'] - h), (xc, y['accept'] + d)])

    # Accept? -> Commit -> Cost < best? -> Save best ; Undo
    arrow(ax, [(xc - DIA_W / 2, y['accept']), (xl, y['accept']), (xl, y['branch'] + h)],
          label='Yes', label_at=1, label_offset=(-0.5, 0.05))
    arrow(ax, [(xc + DIA_W / 2, y['accept']), (xr, y['accept']), (xr, y['branch'] + h)],
          label='No', label_at=1, label_offset=(0.05, 0.05))
    arrow(ax, [(xl, y['branch'] - h), (xl, y['best'] + d)])
    arrow(ax, [(xl, y['best'] - d), (xl, y['save'] + h)],
          label='Yes', label_at=0, label_offset=(0.08, -0.32))
    x_no = -0.45
    ax.plot([xl + w_best / 2, x_no, x_no], [y['best'], y['best'], y['merge']], color=INK,
            linewidth=1.4, zorder=1)
    ax.text(xl + w_best / 2 + 0.08, y['best'] + 0.05, 'No', fontsize=11, color='#52514e',
            ha='left', va='bottom')
    ax.plot([xl, xl], [y['save'] - h, y['merge']], color=INK, linewidth=1.4, zorder=1)
    ax.plot([xr, xr], [y['branch'] - h, y['merge']], color=INK, linewidth=1.4, zorder=1)
    ax.plot([xl, xr], [y['merge'], y['merge']], color=INK, linewidth=1.4, zorder=1)
    arrow(ax, [(xc, y['merge']), (xc, y['update'] + h)])
    arrow(ax, [(xc, y['update'] - h), (xc, y['stalled'] + d)])

    # Stalled or frozen? No -> next move
    arrow(ax, [(xc - w_stall / 2, y['stalled']), (x_loop_l, y['stalled']), (x_loop_l, y['join']),
               (xc, y['join'])],
          label='No', label_at=0, label_offset=(-0.5, 0.05))
    arrow(ax, [(xc, y['stalled'] - d), (xc, y['last'] + d)],
          label='Yes', label_at=0, label_offset=(0.08, -0.32))

    # Last round? No -> next round
    arrow(ax, [(xc + w_last / 2, y['last']), (x_loop_r, y['last']), (x_loop_r, y['set']),
               (xc + BOX_W / 2, y['set'])],
          label='No', label_at=0, label_offset=(0.1, 0.05))
    arrow(ax, [(xc, y['last'] - d), (xc, y['write'] + h)],
          label='Yes', label_at=0, label_offset=(0.08, -0.32))
    arrow(ax, [(xc, y['write'] - h), (xc, y['end'] + h)])

    ax.set_xlim(-5.3, 4.9)
    ax.set_ylim(-17.95, 0.5)
    ax.set_aspect('equal')
    ax.axis('off')
    save(fig, 'flow_final')


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


# ---------------------------------------------------------------------------
# 6. Best-solution rule: which placements replace the best one
# ---------------------------------------------------------------------------
def best_rule():
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.9))
    bx, by = 0.45, 0.62
    for ax, rule in zip(axes, ('old', 'new')):
        ax.set_xlim(0.3, 0.6)
        ax.set_ylim(0.52, 0.72)
        if rule == 'old':
            ax.add_patch(Rectangle((0.3, 0.52), bx - 0.3, by - 0.52, facecolor='#dce9f9',
                                   edgecolor='none', zorder=0))
        else:
            ax.add_patch(Polygon([(0.3, 0.52), (0.3, bx + by - 0.3), (bx + by - 0.52, 0.52)],
                                 facecolor='#fbe1d6', edgecolor='none', zorder=0))
            xs = [0.3, 0.6]
            ax.plot(xs, [bx + by - x for x in xs], color=MOVED, linewidth=1.6, linestyle=(0, (5, 3)))
        ax.plot([bx, bx], [0.52, 0.72], color=MUTED, linewidth=1, linestyle=':')
        ax.plot([0.3, 0.6], [by, by], color=MUTED, linewidth=1, linestyle=':')
        ax.plot(bx, by, 'o', color=INK, markersize=9, zorder=3)
        ax.text(bx + 0.006, by + 0.006, 'best', fontsize=12, fontweight='bold', color=INK)
        ax.plot(0.37, 0.67, 'o', color=MOVED, markersize=8, zorder=3)
        ax.text(0.376, 0.676, 'A', fontsize=12, fontweight='bold', color=MOVED)
        ax.set_xlabel('HPWL / HPWL_init')
        ax.set_ylabel('CC / CC_init')
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
        ax.set_title(rule, fontsize=14, fontweight='bold', color=INK, loc='left')
    fig.subplots_adjust(wspace=0.25)
    save(fig, 'best_rule')


# ---------------------------------------------------------------------------
# 7. Range-limited moves: large window early, R_limit = 1 late (swap)
# ---------------------------------------------------------------------------
def range_limit():
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
    others = [(1, 9), (3, 2), (6, 8), (8, 1), (9, 6), (2, 6), (4, 4), (7, 5), (6, 5), (5, 6), (4, 6)]

    def window(ax, cx, cy, r, n):
        x0, x1 = max(0, cx - r), min(n - 1, cx + r) + 1
        y0, y1 = max(0, cy - r), min(n - 1, cy + r) + 1
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor='#fdf1ea', edgecolor=MOVED,
                               linewidth=2.2, zorder=1))

    # large R_limit: move to an empty site far away inside the window
    ax = axes[0]
    grid(ax, 11, 11)
    window(ax, 5, 5, 3, 11)
    for x, y in others:
        block(ax, x, y)
    block(ax, 5, 5, label='b', fill='#fbe1d6', edge=MOVED)
    block(ax, 7, 2, ghost=True, edge=MOVED)
    move(ax, (5, 5), (7, 2))
    ax.add_patch(FancyArrowPatch((5.15, 5.5), (2.0, 5.5), arrowstyle='<->', mutation_scale=12,
                                 color=INK, linewidth=1.4, shrinkA=0, shrinkB=0, zorder=6))
    ax.text(3.55, 5.62, 'R_limit', fontsize=12, fontweight='bold', color=INK, ha='center',
            va='bottom', zorder=6, bbox=dict(boxstyle='round,pad=0.1', facecolor='white', edgecolor='none'))

    # R_limit = 1: only the 8 neighbours; an occupied target means a swap
    ax = axes[1]
    grid(ax, 11, 11)
    window(ax, 5, 5, 1, 11)
    for x, y in others:
        block(ax, x, y)
    block(ax, 5, 5, label='b', fill='#fbe1d6', edge=MOVED)
    ax.add_patch(FancyArrowPatch((5.5, 5.12), (6.5, 5.12), arrowstyle='<|-|>', mutation_scale=16,
                                 color=INK, linewidth=2, shrinkA=0, shrinkB=0,
                                 connectionstyle='arc3,rad=0.9', zorder=6))
    ax.text(5.5, 3.85, 'R_limit = 1', fontsize=12, fontweight='bold', color=INK, ha='center',
            va='top', zorder=6, bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none'))

    fig.subplots_adjust(wspace=0.12)
    save(fig, 'range_limit')


# ---------------------------------------------------------------------------
# 8. Round schedule: temperature and move range over the 5 rounds (schematic)
# ---------------------------------------------------------------------------
def round_schedule():
    import numpy as np
    chip = 1.0
    fig, (ax_t, ax_r) = plt.subplots(2, 1, figsize=(12, 6.4), sharex=True,
                                     gridspec_kw={'height_ratios': [1.3, 1]})
    t0 = 1e6
    lengths = [10, 6, 4.5, 3.5, 3]   # iterations per round (schematic)
    u_reheat = 0.25 + np.log(2) / 14  # where round 1's move range reaches half the chip
    t_reheat = 10 ** (np.log10(t0) - 0.6 - 3.2 * u_reheat)
    starts_t = [t0] + [t_reheat * 0.66 ** k for k in range(4)]
    x = 0.0
    reheat_x = None
    for k, (length, ts) in enumerate(zip(lengths, starts_t)):
        xs = np.linspace(x, x + length, 200)
        u = (xs - x) / length
        # temperature: log-linear decay; round 1 drops fast at first (accept rate > 0.95)
        if k == 0:
            log_t = np.log10(ts) - 0.6 * np.minimum(u / 0.05, 1) - 3.2 * u
        else:
            log_t = np.log10(ts) - 2.0 * u
        ax_t.plot(xs, 10 ** log_t, color=INK, linewidth=2)
        # move range: full chip until the acceptance rate drops, then shrinks to 1
        if k == 0:
            r = np.where(u < 0.25, chip, np.maximum(chip * np.exp(-(u - 0.25) * 14), 0.02))
            reheat_x = x + length * u_reheat
            reheat_t = t_reheat
        else:
            r = np.maximum(chip / 2 * np.exp(-u * 12), 0.02)
        ax_r.plot(xs, r, color='#eda100', linewidth=2)
        ax_t.plot(x + length, 10 ** log_t[-1], 'x', color=MOVED, markersize=10, mew=2.5, zorder=4)
        ax_r.text(x + length / 2, 1.07, f"round {k + 1}", ha='center', va='bottom', fontsize=11,
                  color='#52514e')
        if k % 2 == 1:
            for ax in (ax_t, ax_r):
                ax.axvspan(x, x + length, color='#f3f2ee', zorder=0, linewidth=0)
        x += length

    # T_reheat: where round 1's move range first reaches half the chip
    ax_t.plot([reheat_x, lengths[0]], [reheat_t, reheat_t], color=MOVED, linewidth=1.2, linestyle=':')
    ax_r.plot([reheat_x, reheat_x], [0, chip / 2], color=MOVED, linewidth=1.2, linestyle=':')
    ax_t.plot([reheat_x, reheat_x], [1e0, reheat_t], color=MOVED, linewidth=1.2, linestyle=':')
    ax_t.text(lengths[0] + 0.15, reheat_t * 1.3, 'T_reheat', fontsize=12, color=MOVED, fontweight='bold')
    ax_t.text(0.15, t0 * 1.3, 'T_0', fontsize=12, color=INK, fontweight='bold')
    ax_t.text(lengths[0] + lengths[1] + 0.15, starts_t[2] * 1.3, '× 0.66', fontsize=12, color=MOVED,
              fontweight='bold')
    ax_t.text(sum(lengths) + 0.45, 10 ** (np.log10(starts_t[4]) - 2.0), 'early stop', fontsize=12,
              color=MOVED, fontweight='bold', va='center')

    ax_t.set_yscale('log')
    ax_t.set_ylim(1e0, 2e7)
    ax_t.set_ylabel('T')
    ax_t.set_yticks([])
    ax_t.minorticks_off()
    ax_r.set_ylim(0, 1.2)
    ax_r.set_yticks([0.02, 0.5, 1.0])
    ax_r.set_yticklabels(['1', 'chip / 2', 'chip'])
    ax_r.set_ylabel('R_limit', labelpad=12)
    ax_r.set_xticks([])
    ax_r.set_xlabel('iteration')
    ax_r.set_xlim(0, sum(lengths) + 3.0)
    for ax in (ax_t, ax_r):
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
    fig.subplots_adjust(hspace=0.12)
    save(fig, 'round_schedule')


# ---------------------------------------------------------------------------
# 9-11. Guided moves: optimal region, its cost function, and the target choice
# ---------------------------------------------------------------------------
GUIDED_NETS = {  # other terminals of the three nets of block b
    'net 1': [(1, 6), (3, 7)],
    'net 2': [(6, 6), (7, 3)],
    'net 3': [(2, 2), (4, 1)],
}
GUIDED_COLORS = {'net 1': NET1, 'net 2': '#1baf7a', 'net 3': '#eda100'}
GUIDED_B = (8, 0)


def guided_spans():
    """Per net, the bounding box [x0, x1) x [y0, y1) of the other terminals (blocks occupy one cell)"""
    spans = {}
    for name, pts in GUIDED_NETS.items():
        spans[name] = (min(p[0] for p in pts), max(p[0] for p in pts) + 1,
                       min(p[1] for p in pts), max(p[1] for p in pts) + 1)
    return spans


def median_range(lo, hi):
    breaks = sorted(list(lo) + [h - 1 for h in hi])
    k = len(lo)
    return breaks[k - 1], breaks[k]


def guided_region():
    spans = guided_spans()
    rx = median_range([s[0] for s in spans.values()], [s[1] for s in spans.values()])
    ry = median_range([s[2] for s in spans.values()], [s[3] for s in spans.values()])
    fig, ax = plt.subplots(figsize=(7.4, 6.6))
    grid(ax, 10, 9)
    ax.add_patch(Rectangle((rx[0], ry[0]), rx[1] - rx[0] + 1, ry[1] - ry[0] + 1, facecolor='#d3f0e5',
                           edgecolor=ANCHOR, linewidth=2.4, zorder=1))
    ax.text(rx[0] + (rx[1] - rx[0] + 1) / 2, ry[0] + (ry[1] - ry[0] + 1) / 2, 'optimal region',
            ha='center', va='center', rotation=90, fontsize=13, fontweight='bold', color=ANCHOR, zorder=6)
    label_pos = {'net 1': 'tl', 'net 2': 'tr', 'net 3': 'bl'}
    for name, (x0, x1, y0, y1) in spans.items():
        color = GUIDED_COLORS[name]
        bbox(ax, x0, x1, y0, y1, color, dashed=True, inset=0.06, label=name, label_pos=label_pos[name])
        for x, y in GUIDED_NETS[name]:
            block(ax, x, y, fill='white', edge=color)
    block(ax, *GUIDED_B, label='b', fill='#fbe1d6', edge=MOVED)
    move(ax, GUIDED_B, (rx[1], ry[0] + 1))
    save(fig, 'guided_region')


def guided_cost():
    import numpy as np
    spans = guided_spans()
    lo = [s[0] for s in spans.values()]
    hi = [s[1] for s in spans.values()]
    a, b = median_range(lo, hi)
    ps = np.arange(0, 10)
    cost = [sum(max(h, p + 1) - min(l, p) for l, h in zip(lo, hi)) for p in ps]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.axvspan(a, b, color='#d3f0e5', zorder=0)
    ax.plot(ps, cost, color=INK, linewidth=2, marker='o', markersize=6, zorder=3)
    ax.plot(GUIDED_B[0], cost[GUIDED_B[0]], 'o', color=MOVED, markersize=11, zorder=4)
    ax.text(GUIDED_B[0], cost[GUIDED_B[0]] + 0.6, 'b', ha='center', va='bottom', fontsize=13,
            fontweight='bold', color=MOVED)
    ax.text((a + b) / 2, min(cost) - 1.0, 'optimal region', ha='center', va='top', fontsize=12,
            fontweight='bold', color=ANCHOR)
    for row, (name, l, h) in enumerate(zip(spans, lo, hi)):
        color = GUIDED_COLORS[name]
        y_bar = max(cost) + 1.0 + 1.1 * row
        ax.plot([l, h - 1], [y_bar] * 2, color=color, linewidth=5, solid_capstyle='butt')
        ax.text(h - 1 + 0.2, y_bar, name, va='center', fontsize=11, color=color, fontweight='bold')
    ax.set_xticks(ps)
    ax.set_xlabel('x of b')
    ax.set_ylabel('total x-span of the nets of b')
    ax.set_ylim(min(cost) - 2.4, max(cost) + 3.9)
    ax.set_xlim(-0.5, 10.4)
    ax.set_yticks([])
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    save(fig, 'guided_cost')


def guided_target():
    spans = guided_spans()
    rx = median_range([s[0] for s in spans.values()], [s[1] for s in spans.values()])
    ry = median_range([s[2] for s in spans.values()], [s[3] for s in spans.values()])
    cols, rows = 10, 9
    U = [[3, 4, 5, 5, 4, 3, 3, 2, 2, 1],
         [4, 5, 6, 7, 6, 5, 4, 3, 2, 2],
         [4, 6, 8, 9, 8, 7, 5, 4, 3, 2],
         [5, 7, 9, 11, 9, 8, 6, 4, 3, 2],
         [5, 7, 9, 10, 7, 8, 6, 5, 3, 2],
         [4, 6, 8, 9, 6, 7, 6, 4, 3, 2],
         [3, 5, 7, 8, 8, 6, 5, 4, 2, 1],
         [3, 4, 5, 6, 5, 5, 4, 3, 2, 1],
         [2, 3, 4, 4, 4, 3, 3, 2, 1, 1]]  # U[y][x], y = 0 at the bottom
    occupied = {(3, 3), (4, 5), (3, 6), (1, 6), (6, 6), (7, 3), (2, 2), (4, 1), (3, 7)}
    samples = [(3, 3), (4, 4), (3, 5), (4, 6)]
    empty = [p for p in samples if p not in occupied]
    chosen = min(empty, key=lambda p: U[p[1]][p[0]])

    cmap = matplotlib.colormaps['Oranges']
    fig, ax = plt.subplots(figsize=(7.4, 6.6))
    grid(ax, cols, rows)
    for y in range(rows):
        for x in range(cols):
            inside = rx[0] <= x <= rx[1] and ry[0] <= y <= ry[1]
            ax.add_patch(Rectangle((x, y), 1, 1, facecolor=cmap(0.06 + U[y][x] / 16),
                                   edgecolor=GRID, linewidth=0.8, alpha=1 if inside else 0.35, zorder=0))
            if inside and (x, y) not in occupied:
                ax.text(x + 0.5, y + 0.5, str(U[y][x]), ha='center', va='center', fontsize=13,
                        fontweight='bold', color=INK, zorder=6)
    ax.add_patch(Rectangle((rx[0], ry[0]), rx[1] - rx[0] + 1, ry[1] - ry[0] + 1, facecolor='none',
                           edgecolor=ANCHOR, linewidth=2.4, zorder=2))
    ax.text(rx[0] + (rx[1] - rx[0] + 1) / 2, ry[1] + 1.12, 'optimal region', ha='center',
            va='bottom', fontsize=12, fontweight='bold', color=ANCHOR, zorder=6,
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white', edgecolor='none'))
    for x, y in occupied:
        block(ax, x, y)
    for x, y in samples:
        ax.add_patch(Ellipse((x + 0.5, y + 0.5), 0.95, 0.95, facecolor='none', edgecolor=INK,
                             linewidth=1.6, linestyle=(0, (3, 2)), zorder=4))
    ax.add_patch(Ellipse((chosen[0] + 0.5, chosen[1] + 0.5), 0.95, 0.95, facecolor='none',
                         edgecolor=MOVED, linewidth=2.6, zorder=5))
    block(ax, *GUIDED_B, label='b', fill='#fbe1d6', edge=MOVED)
    move(ax, GUIDED_B, chosen)
    ax.text(cols + 0.15, rows - 0.5, 'U', fontsize=14, fontweight='bold', color=INK, va='center')
    save(fig, 'guided_target')


if __name__ == '__main__':
    flow_chart()
    flow_chart_final()
    bbox_update()
    anchor_check()
    net_filter()
    u_update()
    best_rule()
    range_limit()
    round_schedule()
    guided_region()
    guided_cost()
    guided_target()
