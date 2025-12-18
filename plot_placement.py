#!/usr/bin/env python3
"""
FPGA Placement Visualizer
Reads input and output files and plots the block placement with nets
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import sys
import argparse
from pathlib import Path
import numpy as np


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


class FPGAPlotter:
    def __init__(self, parser, show_nets=True, show_io_names=True, show_block_names=True, 
                 net_mode='density'):
        """
        Initialize plotter
        
        Args:
            parser: FPGAPlacementParser instance
            show_nets: Whether to draw net information
            show_io_names: Whether to label IO pins
            show_block_names: Whether to label blocks
            net_mode: How to visualize nets ('density', 'bboxes', 'lines', 'hpwl', 'none')
        """
        self.parser = parser
        self.show_nets = show_nets
        self.show_io_names = show_io_names
        self.show_block_names = show_block_names
        self.net_mode = net_mode  # 'density', 'bboxes', 'lines', 'hpwl', 'none'
    
    def _calculate_hpwl(self):
        """Calculate HPWL for all nets"""
        net_hpwls = {}
        for net_name, terminals in self.parser.nets.items():
            positions = []
            for terminal in terminals:
                if terminal in self.parser.blocks:
                    positions.append(self.parser.blocks[terminal])
                elif terminal in self.parser.ios:
                    positions.append(self.parser.ios[terminal])
            
            if len(positions) < 2:
                net_hpwls[net_name] = 0
                continue
            
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            hpwl = (max(xs) - min(xs)) + (max(ys) - min(ys))
            net_hpwls[net_name] = hpwl
        
        return net_hpwls
    
    def plot(self, figsize=(14, 10), save_to=None):
        """
        Generate and display the placement plot
        
        Args:
            figsize: Tuple of (width, height) for figure
            save_to: Path to save the figure (optional)
        """
        fig, ax = plt.subplots(figsize=figsize)
        
        # Draw grid
        self._draw_grid(ax)
        
        # Draw IOs
        self._draw_ios(ax)
        
        # Draw nets (if enabled)
        if self.show_nets:
            self._draw_nets(ax)
        
        # Draw blocks
        self._draw_blocks(ax)
        
        # Set axis properties
        ax.set_xlim(-1, self.parser.C + 1)
        ax.set_ylim(-1, self.parser.R + 1)
        ax.set_aspect('equal')
        ax.invert_yaxis()  # Match typical grid coordinates
        
        ax.set_xlabel('X Coordinate', fontsize=12)
        ax.set_ylabel('Y Coordinate', fontsize=12)
        ax.set_title(f'FPGA Placement (Grid: {self.parser.C}x{self.parser.R})', fontsize=14, fontweight='bold')
        
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.set_axisbelow(True)
        
        if save_to:
            fig.savefig(save_to, dpi=150, bbox_inches='tight')
            print(f"Plot saved to {save_to}")
        
        plt.tight_layout()
        return fig, ax
    
    def _draw_grid(self, ax):
        """Draw the FPGA grid"""
        for x in range(self.parser.C + 1):
            ax.axvline(x - 0.5, color='gray', linewidth=0.5, alpha=0.2)
        for y in range(self.parser.R + 1):
            ax.axhline(y - 0.5, color='gray', linewidth=0.5, alpha=0.2)
    
    def _draw_blocks(self, ax):
        """Draw logic blocks"""
        for block_name, (x, y) in self.parser.blocks.items():
            # Draw block as a square
            rect = patches.Rectangle((x - 0.4, y - 0.4), 0.8, 0.8, 
                                     linewidth=2, edgecolor='blue', 
                                     facecolor='lightblue', alpha=0.7)
            ax.add_patch(rect)
            
            # Add label
            if self.show_block_names:
                ax.text(x, y, block_name[:8], ha='center', va='center', 
                       fontsize=8, fontweight='bold', color='darkblue')
    
    def _draw_ios(self, ax):
        """Draw IO pins"""
        for io_name, (x, y) in self.parser.ios.items():
            # Draw IO as a circle
            circle = patches.Circle((x, y), 0.2, linewidth=2, 
                                   edgecolor='red', facecolor='lightcoral', alpha=0.8)
            ax.add_patch(circle)
            
            # Add label
            if self.show_io_names:
                offset_x = 0.4 if x < self.parser.C / 2 else -0.4
                offset_y = 0.4 if y < self.parser.R / 2 else -0.4
                ax.text(x + offset_x, y + offset_y, io_name, ha='center', va='center',
                       fontsize=7, color='darkred', bbox=dict(boxstyle='round,pad=0.3', 
                       facecolor='white', alpha=0.7, edgecolor='none'))
    
    def _draw_nets(self, ax):
        """Draw net connections based on selected mode"""
        if self.net_mode == 'density':
            self._draw_nets_density(ax)
        elif self.net_mode == 'bboxes':
            self._draw_nets_bboxes(ax)
        elif self.net_mode == 'lines':
            self._draw_nets_lines(ax)
        elif self.net_mode == 'hpwl':
            self._draw_nets_hpwl(ax)
    
    def _draw_nets_density(self, ax):
        """Draw net density heatmap"""
        # Create density map
        density_map = np.zeros((int(self.parser.R), int(self.parser.C)))
        
        for net_name, terminals in self.parser.nets.items():
            # Get positions of all terminals
            positions = []
            for terminal in terminals:
                if terminal in self.parser.blocks:
                    positions.append(self.parser.blocks[terminal])
                elif terminal in self.parser.ios:
                    positions.append(self.parser.ios[terminal])
            
            if len(positions) < 2:
                continue
            
            # Calculate bounding box for this net
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # Mark cells covered by this net
            x_start = max(0, int(np.floor(min_x)))
            x_end = min(int(self.parser.C), int(np.ceil(max_x)) + 1)
            y_start = max(0, int(np.floor(min_y)))
            y_end = min(int(self.parser.R), int(np.ceil(max_y)) + 1)
            
            density_map[y_start:y_end, x_start:x_end] += 1
        
        # Plot heatmap
        im = ax.imshow(density_map, cmap='YlOrRd', alpha=0.5, 
                       extent=[-0.5, self.parser.C - 0.5, self.parser.R - 0.5, -0.5],
                       aspect='auto', interpolation='bilinear')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, label='Net Density')
    
    def _draw_nets_bboxes(self, ax):
        """Draw bounding boxes for each net"""
        colors = plt.cm.tab20(np.linspace(0, 1, min(20, len(self.parser.nets))))
        
        for net_idx, (net_name, terminals) in enumerate(self.parser.nets.items()):
            if len(terminals) < 2:
                continue
            
            # Get positions of all terminals
            positions = []
            for terminal in terminals:
                if terminal in self.parser.blocks:
                    positions.append(self.parser.blocks[terminal])
                elif terminal in self.parser.ios:
                    positions.append(self.parser.ios[terminal])
            
            if len(positions) < 2:
                continue
            
            # Calculate bounding box
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            
            color = colors[net_idx % len(colors)]
            rect = patches.Rectangle((min_x - 0.5, min_y - 0.5), width, height,
                                    linewidth=0.5, edgecolor=color, facecolor='none',
                                    alpha=0.4)
            ax.add_patch(rect)
    
    def _draw_nets_lines(self, ax):
        """Draw net connections as radial lines (original method)"""
        colors = plt.cm.tab20(np.linspace(0, 1, len(self.parser.nets)))
        
        for net_idx, (net_name, terminals) in enumerate(self.parser.nets.items()):
            if len(terminals) < 2:
                continue
            
            # Get positions of all terminals
            positions = []
            for terminal in terminals:
                if terminal in self.parser.blocks:
                    positions.append(self.parser.blocks[terminal])
                elif terminal in self.parser.ios:
                    positions.append(self.parser.ios[terminal])
            
            if len(positions) < 2:
                continue
            
            # Draw Steiner tree (simple: connect all to centroid)
            color = colors[net_idx % len(colors)]
            
            # Calculate centroid
            cx = sum(p[0] for p in positions) / len(positions)
            cy = sum(p[1] for p in positions) / len(positions)
            
            # Draw lines from each terminal to centroid
            for px, py in positions:
                ax.plot([px, cx], [py, cy], color=color, alpha=0.3, linewidth=0.8)
        
        # Add legend (sample of nets)
        num_nets_to_show = min(5, len(self.parser.nets))
        legend_elements = [patches.Patch(facecolor=colors[i % len(colors)], 
                                        alpha=0.3, label=f'Nets...')
                          for i in range(num_nets_to_show)]
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
    
    def _draw_nets_hpwl(self, ax):
        """Draw nets colored by HPWL magnitude"""
        # Calculate HPWL for all nets
        net_hpwls = self._calculate_hpwl()
        
        if not net_hpwls:
            return
        
        # Get max HPWL for normalization
        max_hpwl = max(net_hpwls.values()) if net_hpwls else 1
        
        # Create colormap
        cmap = plt.cm.RdYlGn_r  # Red (high) to Green (low)
        
        # Draw each net with color based on HPWL
        for net_name, terminals in self.parser.nets.items():
            if len(terminals) < 2:
                continue
            
            # Get positions of all terminals
            positions = []
            for terminal in terminals:
                if terminal in self.parser.blocks:
                    positions.append(self.parser.blocks[terminal])
                elif terminal in self.parser.ios:
                    positions.append(self.parser.ios[terminal])
            
            if len(positions) < 2:
                continue
            
            # Calculate bounding box
            xs = [p[0] for p in positions]
            ys = [p[1] for p in positions]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # Get HPWL and normalize for color
            hpwl = net_hpwls.get(net_name, 0)
            color_intensity = hpwl / max_hpwl if max_hpwl > 0 else 0
            color = cmap(color_intensity)
            
            # Draw bounding box
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            
            rect = patches.Rectangle((min_x - 0.5, min_y - 0.5), width, height,
                                    linewidth=1.0, edgecolor=color, facecolor='none',
                                    alpha=0.6)
            ax.add_patch(rect)
        
        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, 
                                   norm=plt.Normalize(vmin=0, vmax=max_hpwl))
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, label='HPWL (Half-Perimeter Wire Length)')
    
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


def main():
    parser_args = argparse.ArgumentParser(
        description='FPGA Placement Visualizer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Plot final placement with density heatmap
  python plot_placement.py testcases/alu4.txt result/alu4.out --mode density
  
  # Plot both initial and final placements
  python plot_placement.py testcases/alu4.txt result/alu4.out --both --mode density
  
  # Plot with bounding boxes instead of density
  python plot_placement.py testcases/alu4.txt result/alu4.out --mode bboxes
  
  # Plot with HPWL-based coloring (red=long, green=short)
  python plot_placement.py testcases/alu4.txt result/alu4.out --mode hpwl
  
  # Plot without nets
  python plot_placement.py testcases/alu4.txt result/alu4.out --mode none
        ''')
    
    parser_args.add_argument('input', help='Input testcase file')
    parser_args.add_argument('output', nargs='?', help='Output placement file (optional)')
    parser_args.add_argument('--save', help='Save plot to file (or directory if --both)')
    parser_args.add_argument('--both', action='store_true', 
                            help='Plot both initial and final placements')
    parser_args.add_argument('--mode', choices=['density', 'bboxes', 'lines', 'hpwl', 'none'],
                            default='density', help='Net visualization mode')
    parser_args.add_argument('--no-io-names', action='store_true', help='Do not label IOs')
    parser_args.add_argument('--show-block-names', action='store_true', help='Label blocks with names')
    parser_args.add_argument('--figsize', type=float, nargs=2, default=[14, 10],
                           help='Figure size (width height)')
    
    args = parser_args.parse_args()
    
    # Validate arguments
    if args.both and not args.output:
        print("Error: --both requires both input and output files")
        sys.exit(1)
    
    # Parse files
    try:
        parser_final = FPGAPlacementParser(args.input, args.output) if args.output else None

        # If an output file is provided, try to load the companion *_init.txt produced by main.cpp
        init_output_path = None
        if args.output:
            base_no_ext = Path(args.output).with_suffix("")
            init_output_path = f"{base_no_ext}_init.txt"
            if not Path(init_output_path).exists():
                print(f"Warning: initial placement file not found at {init_output_path}; falling back to unplaced blocks")
                init_output_path = None

        parser_initial = FPGAPlacementParser(args.input, init_output_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Determine what to plot
    to_plot = []
    if args.both and parser_final:
        to_plot.append(('Initial', parser_initial))
        to_plot.append(('Final', parser_final))
    elif parser_final:
        to_plot.append(('Final', parser_final))
    else:
        to_plot.append(('Initial', parser_initial))
    
    # Plot each
    for plot_type, parser in to_plot:
        plotter = FPGAPlotter(
            parser,
            show_nets=args.mode != 'none',
            show_io_names=not args.no_io_names,
            show_block_names=args.show_block_names,
            net_mode=args.mode
        )
        
        # Print statistics
        print(f"\n{plot_type.upper()} PLACEMENT:")
        plotter.print_statistics()
        
        # Determine output file
        output_file = None
        if args.save:
            if args.both:
                # Save to directory with type in filename
                output_file = f"{args.save.rstrip('/')}/{plot_type.lower()}_placement.png"
            else:
                output_file = args.save
        
        # Plot
        fig, ax = plotter.plot(figsize=tuple(args.figsize), save_to=output_file)
        
        if not args.save:
            plt.show()
        else:
            plt.close(fig)


if __name__ == '__main__':
    main()
