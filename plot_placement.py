#!/usr/bin/env python3
"""
FPGA Placement Visualizer
Reads input and output files and plots the initial and final placement side by side,
with nets drawn on one shared color scale.

Geometry follows src/Solver.cpp:
  - a block at (x, y) occupies cell [x, x+1] x [y, y+1]; an IO is a point on the boundary
  - U[x][y] counts net bounding boxes covering cell (x, y), for ceil(min) <= x < max
  - CC = N * sum(U^2) / sum(U)^2 = 1 + (std(U) / mean(U))^2
"""

import argparse
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PatchCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm
import matplotlib.patches as patches
import numpy as np

# Palette: categorical slots 1/2 for final/initial, one-hue sequential for magnitude,
# blue -> neutral gray -> red diverging for U / mean(U)
COLOR_INITIAL = '#eb6834'
COLOR_FINAL = '#2a78d6'
TEXT_PRIMARY = '#0b0b0b'
TEXT_SECONDARY = '#52514e'
GRID_COLOR = '#d9d8d4'
SEQUENTIAL = LinearSegmentedColormap.from_list(
    'orange_seq', ['#fbf3ee', '#f6c9b3', '#eb6834', '#a63d12', '#4f1a05'])
DIVERGING = LinearSegmentedColormap.from_list(
    'cool_neutral_warm', ['#1c5cab', '#8fb8e8', '#f0efec', '#f0a07e', '#b8321a'])


class FPGAPlacementParser:
    def __init__(self, input_file, output_file=None):
        """
        Initialize parser with input and output files
        
        Args:
            input_file: Path to testcase input file
            output_file: Path to placement output file (optional)
        """
        self.input_file = input_file
        self.output_file = output_file
        
        # Parsed data
        self.R = 0  # rows
        self.C = 0  # columns
        self.blocks = {}  # {block_name: (x, y)}
        self.ios = {}  # {io_name: (x, y)}
        self.nets = {}  # {net_name: [connected_terminals]}
        
        self.parse_input()
        if output_file:
            self.parse_output()
    
    def parse_input(self):
        """Parse the testcase input file"""
        with open(self.input_file, 'r') as f:
            lines = f.readlines()
        
        idx = 0
        
        # Parse header
        header = lines[idx].strip().split()
        self.R, self.C = int(header[0]), int(header[1])
        numLBs = int(header[2])
        numIOs = int(header[3])
        numNets = int(header[4])
        idx += 1
        
        # Parse logic blocks (positions will be filled from output)
        for i in range(numLBs):
            block_name = lines[idx].strip()
            self.blocks[block_name] = (0, 0)  # Placeholder
            idx += 1
        
        # Parse IOs
        for i in range(numIOs):
            parts = lines[idx].strip().split()
            io_name = parts[0]
            x, y = float(parts[1]), float(parts[2])
            self.ios[io_name] = (x, y)
            idx += 1
        
        # Parse nets
        for i in range(numNets):
            parts = lines[idx].strip().split()
            net_name = parts[0]
            degree = int(parts[1])
            terminals = parts[2:2+degree]
            self.nets[net_name] = terminals
            idx += 1
    
    def parse_output(self):
        """Parse the placement output file"""
        with open(self.output_file, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 3:
                block_name = parts[0]
                x, y = int(parts[1]), int(parts[2])
                if block_name in self.blocks:
                    self.blocks[block_name] = (x, y)


class PlacementMetrics:
    def __init__(self, parser):
        """
        Compute per-net bounding boxes, HPWL and the coverage map U for one placement

        Args:
            parser: FPGAPlacementParser instance with block positions filled in
        """
        self.parser = parser
        self.C = int(parser.C)
        self.R = int(parser.R)
        self.bboxes = {}  # {net_name: (x_min, x_max, y_min, y_max)}
        self.net_hpwl = {}  # {net_name: hpwl}
        self.U = np.zeros((self.C, self.R), dtype=np.int64)  # indexed [x][y] like Solver.cpp

        self._compute()

    def _compute(self):
        for net_name, terminals in self.parser.nets.items():
            x_min, x_max = float(self.C), 0.0
            y_min, y_max = float(self.R), 0.0
            for terminal in terminals:
                if terminal in self.parser.blocks:
                    bx, by = self.parser.blocks[terminal]
                    x_min, x_max = min(x_min, bx), max(x_max, bx + 1)
                    y_min, y_max = min(y_min, by), max(y_max, by + 1)
                elif terminal in self.parser.ios:
                    ix, iy = self.parser.ios[terminal]
                    x_min, x_max = min(x_min, ix), max(x_max, ix)
                    y_min, y_max = min(y_min, iy), max(y_max, iy)

            self.bboxes[net_name] = (x_min, x_max, y_min, y_max)
            self.net_hpwl[net_name] = (x_max - x_min) + (y_max - y_min)

            # cells x in [ceil(x_min), x_max) -> slice end is ceil(x_max)
            xs, xe = max(0, math.ceil(x_min)), min(self.C, math.ceil(x_max))
            ys, ye = max(0, math.ceil(y_min)), min(self.R, math.ceil(y_max))
            if xs < xe and ys < ye:
                self.U[xs:xe, ys:ye] += 1

    @property
    def hpwl(self):
        return sum(self.net_hpwl.values())

    @property
    def cc(self):
        total = self.U.sum()
        return self.U.size * float((self.U.astype(np.float64) ** 2).sum()) / float(total) ** 2

    @property
    def U_norm(self):
        """Coverage map divided by its mean: 1 = average, CC - 1 = variance of this map"""
        return self.U / self.U.mean()


def style_axes(ax):
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
    ax.xaxis.label.set_color(TEXT_SECONDARY)
    ax.yaxis.label.set_color(TEXT_SECONDARY)


class FPGAPlotter:
    def __init__(self, metrics, show_io_names=True, show_block_names=False, net_mode='density'):
        """
        Initialize plotter for one placement

        Args:
            metrics: PlacementMetrics instance
            show_io_names: Whether to label IO pins
            show_block_names: Whether to label blocks
            net_mode: How to visualize nets ('density', 'cc', 'bboxes', 'lines', 'hpwl', 'none')
        """
        self.metrics = metrics
        self.parser = metrics.parser
        self.show_io_names = show_io_names
        self.show_block_names = show_block_names
        self.net_mode = net_mode

    def plot(self, ax, norm, title):
        """
        Draw the placement onto ax

        Args:
            ax: Matplotlib axes to draw into
            norm: Color normalization shared with the other placement (None for 'bboxes'/'lines'/'none')
            title: Axes title
        Returns:
            A mappable for the shared colorbar, or None
        """
        mappable = self._draw_nets(ax, norm)
        self._draw_grid(ax)
        self._draw_blocks(ax)
        self._draw_ios(ax)

        pad = 1.0
        ax.set_xlim(-pad, self.metrics.C + pad)
        ax.set_ylim(self.metrics.R + pad, -pad)  # y grows downward, matching grid coordinates
        ax.set_aspect('equal')
        ax.set_xlabel('X Coordinate')
        ax.set_ylabel('Y Coordinate')
        ax.set_title(title, fontsize=12, color=TEXT_PRIMARY, loc='left')
        style_axes(ax)
        return mappable

    def _draw_grid(self, ax):
        """Draw the FPGA grid on cell boundaries"""
        C, R = self.metrics.C, self.metrics.R
        lw = 0.4 if max(C, R) <= 40 else 0.2
        segments = [[(x, 0), (x, R)] for x in range(C + 1)] + [[(0, y), (C, y)] for y in range(R + 1)]
        ax.add_collection(LineCollection(segments, colors=GRID_COLOR, linewidths=lw, zorder=2))

    def _draw_blocks(self, ax):
        """Draw logic blocks as outlines only, so the coloring underneath stays visible"""
        rects = [patches.Rectangle((x + 0.12, y + 0.12), 0.76, 0.76)
                 for x, y in self.parser.blocks.values()]
        lw = 0.8 if max(self.metrics.C, self.metrics.R) <= 40 else 0.4
        ax.add_collection(PatchCollection(rects, facecolor='none', edgecolor=TEXT_PRIMARY,
                                          linewidths=lw, alpha=0.55, zorder=3))
        if self.show_block_names:
            for block_name, (x, y) in self.parser.blocks.items():
                ax.text(x + 0.5, y + 0.5, block_name[:8], ha='center', va='center',
                        fontsize=6, color=TEXT_PRIMARY, zorder=4)

    def _draw_ios(self, ax):
        """Draw IO pins on the boundary"""
        xs = [p[0] for p in self.parser.ios.values()]
        ys = [p[1] for p in self.parser.ios.values()]
        ax.scatter(xs, ys, s=22, marker='s', color=TEXT_PRIMARY, edgecolors='white',
                   linewidths=0.6, zorder=5)
        if self.show_io_names and len(self.parser.ios) <= 32:  # labels overlap on larger designs
            C, R = self.metrics.C, self.metrics.R
            for io_name, (x, y) in self.parser.ios.items():
                dx = -0.6 if x <= 0 else (0.6 if x >= C else 0)
                dy = -0.6 if y <= 0 else (0.6 if y >= R else 0)
                ax.text(x + dx, y + dy, io_name, ha='center', va='center', fontsize=6,
                        color=TEXT_SECONDARY, zorder=5)

    def _draw_nets(self, ax, norm):
        """Draw net information based on selected mode"""
        if self.net_mode == 'density':
            return self._draw_heatmap(ax, self.metrics.U, SEQUENTIAL, norm)
        if self.net_mode == 'cc':
            return self._draw_heatmap(ax, self.metrics.U_norm, DIVERGING, norm)
        if self.net_mode == 'hpwl':
            return self._draw_nets_hpwl(ax, norm)
        if self.net_mode == 'bboxes':
            self._draw_nets_bboxes(ax)
        elif self.net_mode == 'lines':
            self._draw_nets_lines(ax)
        return None

    def _draw_heatmap(self, ax, grid, cmap, norm):
        """Draw a per-cell map; grid is indexed [x][y] and cell (x, y) spans [x, x+1] x [y, y+1]"""
        return ax.imshow(grid.T, cmap=cmap, norm=norm, origin='upper', interpolation='nearest',
                         extent=[0, self.metrics.C, self.metrics.R, 0], zorder=1)

    def _draw_nets_bboxes(self, ax):
        """Draw bounding boxes for each net"""
        rects = [patches.Rectangle((x0, y0), x1 - x0, y1 - y0)
                 for x0, x1, y0, y1 in self.metrics.bboxes.values()]
        ax.add_collection(PatchCollection(rects, facecolor='none', edgecolor=COLOR_FINAL,
                                          linewidths=0.6, alpha=0.3, zorder=1))

    def _draw_nets_lines(self, ax):
        """Draw net connections as star lines from each terminal to the net centroid"""
        segments = []
        for terminals in self.parser.nets.values():
            points = []
            for terminal in terminals:
                if terminal in self.parser.blocks:
                    bx, by = self.parser.blocks[terminal]
                    points.append((bx + 0.5, by + 0.5))
                elif terminal in self.parser.ios:
                    points.append(self.parser.ios[terminal])
            if len(points) < 2:
                continue
            cx = sum(p[0] for p in points) / len(points)
            cy = sum(p[1] for p in points) / len(points)
            segments.extend([[p, (cx, cy)] for p in points])
        ax.add_collection(LineCollection(segments, colors=COLOR_FINAL, linewidths=0.6,
                                         alpha=0.3, zorder=1))

    def _draw_nets_hpwl(self, ax, norm):
        """Draw net bounding boxes colored by HPWL, longest on top"""
        items = sorted(self.metrics.net_hpwl.items(), key=lambda kv: kv[1])
        rects, colors = [], []
        for net_name, hpwl in items:
            x0, x1, y0, y1 = self.metrics.bboxes[net_name]
            rects.append(patches.Rectangle((x0, y0), x1 - x0, y1 - y0))
            colors.append(SEQUENTIAL(norm(hpwl)))
        ax.add_collection(PatchCollection(rects, facecolor='none', edgecolors=colors,
                                          linewidths=0.8, alpha=0.7, zorder=1))
        return plt.cm.ScalarMappable(cmap=SEQUENTIAL, norm=norm)

    def print_statistics(self):
        """Print placement statistics"""
        print("\n" + "="*60)
        print("FPGA PLACEMENT STATISTICS")
        print("="*60)
        print(f"Grid Size: {self.parser.C} x {self.parser.R}")
        print(f"Total Cells: {self.parser.C * self.parser.R}")
        print(f"Number of Blocks: {len(self.parser.blocks)}")
        print(f"Number of IOs: {len(self.parser.ios)}")
        print(f"Number of Nets: {len(self.parser.nets)}")
        print(f"HPWL: {self.metrics.hpwl:.1f}")
        print(f"CC: {self.metrics.cc:.6f}")

        # Calculate utilization
        utilization = (len(self.parser.blocks) / (self.parser.C * self.parser.R)) * 100
        print(f"Block Utilization: {utilization:.2f}%")

        # Calculate bounding box
        if self.parser.blocks:
            block_coords = list(self.parser.blocks.values())
            min_x = min(c[0] for c in block_coords)
            max_x = max(c[0] for c in block_coords)
            min_y = min(c[1] for c in block_coords)
            max_y = max(c[1] for c in block_coords)
            print(f"Block Bounding Box: ({min_x}, {min_y}) to ({max_x}, {max_y})")

        print("="*60 + "\n")


def shared_norm(mode, metrics_list):
    """One color normalization covering every placement, so initial and final are comparable"""
    if mode == 'density':
        return Normalize(vmin=0, vmax=max(m.U.max() for m in metrics_list))
    if mode == 'cc':
        vmax = max(m.U_norm.max() for m in metrics_list)
        return TwoSlopeNorm(vmin=0, vcenter=1, vmax=max(vmax, 1.01))
    if mode == 'hpwl':
        return Normalize(vmin=0, vmax=max(max(m.net_hpwl.values()) for m in metrics_list))
    return None


COLORBAR_LABELS = {
    'density': 'U: net bounding boxes covering the cell   (shared scale)',
    'cc': 'U / mean(U)   (1 = average; shared scale)',
    'hpwl': 'Net HPWL   (shared scale)',
}
MODE_TITLES = {
    'density': 'Net density U',
    'cc': 'Congestion: U / mean(U)',
    'hpwl': 'Net bounding boxes by HPWL',
    'bboxes': 'Net bounding boxes',
    'lines': 'Net connections',
    'none': 'Placement',
}


def plot_placements(placements, mode, case_name, save_to, show_io_names, show_block_names, figsize):
    """
    Plot one or more placements side by side on one shared color scale

    Args:
        placements: list of (label, PlacementMetrics)
        mode: Net visualization mode
        case_name: Shown in the figure title
        save_to: Path to save the figure (None to show it)
    """
    fig, axes = plt.subplots(1, len(placements), figsize=figsize, layout='constrained', squeeze=False)
    axes = axes[0]
    norm = shared_norm(mode, [m for _, m in placements])

    mappable = None
    for ax, (label, metrics) in zip(axes, placements):
        plotter = FPGAPlotter(metrics, show_io_names=show_io_names,
                              show_block_names=show_block_names, net_mode=mode)
        title = f"{label}: HPWL = {metrics.hpwl:,.0f},  CC = {metrics.cc:.4f}"
        mappable = plotter.plot(ax, norm, title)

    if mappable is not None:
        cbar = fig.colorbar(mappable, ax=list(axes), shrink=0.85, pad=0.01)
        cbar.set_label(COLORBAR_LABELS[mode], color=TEXT_SECONDARY)
        cbar.ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
        if mode == 'cc':
            cbar.ax.axhline(1.0, color=TEXT_PRIMARY, linewidth=1)

    first, last = placements[0][1], placements[-1][1]
    grid = f"Grid: {first.C}x{first.R}"
    fig.suptitle(f"{case_name}: {MODE_TITLES[mode]}   ({grid})", fontsize=14, fontweight='bold',
                 color=TEXT_PRIMARY, x=0.01, y=1.03, ha='left')

    if save_to:
        Path(save_to).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_to, dpi=150, bbox_inches='tight', facecolor='white')
        print(f"Plot saved to {save_to}")
        plt.close(fig)
    else:
        plt.show()


def load_placements(input_file, output_file):
    """Return [(label, PlacementMetrics)] for the initial (if found) and final placement"""
    placements = []
    if output_file:
        init_file = f"{Path(output_file).with_suffix('')}_init.txt"
        if Path(init_file).exists():
            placements.append(('Initial', PlacementMetrics(FPGAPlacementParser(input_file, init_file))))
        else:
            print(f"Warning: initial placement file not found at {init_file}; plotting final only")
        placements.append(('Final', PlacementMetrics(FPGAPlacementParser(input_file, output_file))))
    else:
        placements.append(('Unplaced', PlacementMetrics(FPGAPlacementParser(input_file))))
    return placements


def main():
    parser_args = argparse.ArgumentParser(
        description='FPGA Placement Visualizer: initial and final placement side by side on a shared scale',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Net density (U), initial | final, shared color scale
  python plot_placement.py testcases/alu4.txt result/alu4.out --mode density --save plot/alu4_density.png

  # Congestion map U / mean(U), centered at 1 (CC = 1 + var of this map)
  python plot_placement.py testcases/alu4.txt result/alu4.out --mode cc --save plot/alu4_cc.png

  # Net bounding boxes colored by HPWL (red=long)
  python plot_placement.py testcases/alu4.txt result/alu4.out --mode hpwl

  # Blocks only
  python plot_placement.py testcases/alu4.txt result/alu4.out --mode none
        ''')

    parser_args.add_argument('input', help='Input testcase file')
    parser_args.add_argument('output', nargs='?',
                             help='Output placement file; its <name>_init.txt is plotted alongside it')
    parser_args.add_argument('--save', help='Save the figure to this file')
    parser_args.add_argument('--mode', choices=['density', 'cc', 'bboxes', 'lines', 'hpwl', 'none'],
                             default='density', help='Net visualization mode')
    parser_args.add_argument('--no-io-names', action='store_true',
                             help='Do not label IOs (always off when there are more than 32 IOs)')
    parser_args.add_argument('--show-block-names', action='store_true', help='Label blocks with names')
    parser_args.add_argument('--figsize', type=float, nargs=2, default=[20, 9.5],
                             help='Figure size (width height)')
    parser_args.add_argument('--stats', action='store_true', help='Print placement statistics')

    args = parser_args.parse_args()

    try:
        placements = load_placements(args.input, args.output)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.stats:
        for label, metrics in placements:
            print(f"\n{label.upper()} PLACEMENT:")
            FPGAPlotter(metrics).print_statistics()

    case_name = Path(args.output or args.input).stem
    plot_placements(placements, args.mode, case_name, args.save,
                    show_io_names=not args.no_io_names,
                    show_block_names=args.show_block_names,
                    figsize=tuple(args.figsize))


if __name__ == '__main__':
    main()
