#!/bin/bash

# Plot all testcases with available output files
# Usage: ./plot_all.sh [mode]
# Modes: density (default), bboxes, lines, hpwl, none

MODE=${1:-density}

# Check if result directory exists
if [ ! -d "result" ]; then
    echo "Error: result/ directory not found"
    exit 1
fi

# Check if plot directory exists, create if not
if [ ! -d "plot" ]; then
    mkdir -p plot
    echo "Created plot/ directory"
fi

echo "=========================================="
echo "FPGA Placement Visualization"
echo "=========================================="
echo "Mode: $MODE"
echo "Saving plots to: plot/"
echo ""

# Counter for processed cases
count=0
total=0

# Iterate over all output files in result/
for output_file in result/*.out; do
    total=$((total + 1))
    
    # Extract case name (filename without extension)
    case_name=$(basename "$output_file" .out)
    input_file="testcases/${case_name}.txt"
    
    # Check if input file exists
    if [ ! -f "$input_file" ]; then
        echo "⚠️  Skipping $case_name: input file not found ($input_file)"
        continue
    fi
    
    echo "📊 Processing: $case_name"
    
    # Clean up existing plots for this case
    rm -f plot/${case_name}_initial.png plot/${case_name}_final.png
    echo "   ✓ Cleared existing plots"
    
    # Run plotter
    if python3 plot_placement.py "$input_file" "$output_file" \
        --both --mode "$MODE" --save plot/ > /dev/null 2>&1; then
        echo "   ✓ Generated initial_placement.png and final_placement.png"
        # Rename to case-specific names
        mv plot/initial_placement.png plot/${case_name}_initial.png 2>/dev/null
        mv plot/final_placement.png plot/${case_name}_final.png 2>/dev/null
        echo "   ✓ Saved as ${case_name}_initial.png and ${case_name}_final.png"
        count=$((count + 1))
    else
        echo "   ✗ Failed to generate plots"
    fi
    echo ""
done

echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Total output files found: $total"
echo "Successfully plotted: $count"
echo "Output location: plot/"
echo ""

if [ $count -gt 0 ]; then
    echo "✓ Done! Generated $((count * 2)) plots"
    ls -lh plot/ | grep -E "(initial|final)" | wc -l
else
    echo "⚠️  No plots were generated"
    exit 1
fi
