#!/bin/bash

# Plot all testcases with available output files
# Usage: ./plot_all.sh [mode]
# Modes: density (default), bboxes, lines, hpwl, none
#
# Per case, writes to plot/:
#   <case>_<mode>.png  initial | final placement, nets drawn in <mode>, shared color scale
#   <case>_cc.png      initial | final congestion map U / mean(U), shared color scale
#   <case>_hpwl.png    per-net HPWL charts (initial vs final)
#   <case>_sa.png      HPWL / CC / cost / temperature over the SA iterations (needs result/<case>_trace.csv)
# plus plot/summary.png comparing all cases (HPWL, CC and runtime); the plots embedded in README.md are copied to docs/figures/results/

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

    # Clean up existing plots for this case (including the old per-placement layout)
    rm -f plot/${case_name}_initial.png plot/${case_name}_final.png plot/${case_name}_metrics.png \
          plot/${case_name}_${MODE}.png plot/${case_name}_cc.png plot/${case_name}_hpwl.png

    ok=1
    for plot_mode in "$MODE" cc; do
        if python3 plot_placement.py "$input_file" "$output_file" \
            --mode "$plot_mode" --save "plot/${case_name}_${plot_mode}.png" > /dev/null 2>&1; then
            echo "   ✓ Saved ${case_name}_${plot_mode}.png"
        else
            echo "   ✗ Failed to generate ${case_name}_${plot_mode}.png"
            ok=0
        fi
    done

    [ $ok -eq 1 ] && count=$((count + 1))
    echo ""
done

echo "📈 Generating HPWL charts and cross-case summary"
if python3 plot_metrics.py --all --save plot/ > /dev/null 2>&1; then
    echo "   ✓ Saved <case>_hpwl.png and summary.png"
else
    echo "   ✗ Failed to generate HPWL charts"
fi
echo ""

echo "🌡️  Generating SA run plots"
if ls result/*_trace.csv > /dev/null 2>&1; then
    if python3 plot_sa.py result/*_trace.csv --save plot/ > /dev/null 2>&1; then
        echo "   ✓ Saved <case>_sa.png"
    else
        echo "   ✗ Failed to generate SA run plots"
    fi
else
    echo "   ⚠️  No result/*_trace.csv found; rerun ./run_tests.sh with SA_TRACE enabled"
fi
echo ""

# Copy the plots embedded in README.md into docs/ (plot/ itself is not tracked)
DOC_PLOTS="summary.png clma_2_sa.png hidden1_cc.png hidden2_cc.png hidden3_cc.png hidden3_sa.png"
mkdir -p docs/figures/results
for f in $DOC_PLOTS; do
    [ -f "plot/$f" ] && cp "plot/$f" docs/figures/results/
done
echo "📄 Copied README plots to docs/figures/results/"
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Total output files found: $total"
echo "Successfully plotted: $count"
echo "Output location: plot/"
echo ""

if [ $count -gt 0 ]; then
    echo "✓ Done!"
else
    echo "⚠️  No plots were generated"
    exit 1
fi
