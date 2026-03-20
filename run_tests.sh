#!/bin/bash

# Function to center text in a field
center_text() {
    local text="$1"
    local width="$2"
    local len=${#text}
    local pad=$(( (width - len) / 2 ))
    local left_pad=$(printf "%${pad}s" "")
    local right_pad=$(printf "%$((width - len - pad))s" "")
    echo "${left_pad}${text}${right_pad}"
}

# make first
make

# for all [case_name].txt in testcases:
# print the upper boundary of the table
printf "| Case Name | Initial Wirelength | Final Wirelength | Initial CC | Final CC | Net count | IO count | Block count |\n"
printf "|-----------|--------------------|------------------|------------|----------|-----------|----------|-------------|\n"

for testcase in testcases/*.txt; do
    case_name=$(basename "$testcase" .txt)
    # run ./placer case_name.txt result/case_name.out > case_name.log
    ./placer "$testcase" "result/${case_name}.out" > "${case_name}.log"

    # Parse current format:
    #   Initial performance: Wirelength = [HPWL], CC = [Congestion Cost]
    #   Final performance: Wirelength = [HPWL], CC = [Congestion Cost]
    # Keep fallback for legacy format:
    #   Initial total wirelength = [HPWL], Initial CC = [Congestion Cost]
    log_file="${case_name}.log"
    initial_wirelength=$(grep -oP 'Initial performance:\s*Wirelength\s*=\s*\K[-0-9.]+' "$log_file" | tail -1)
    initial_CC=$(grep -oP 'Initial performance:\s*Wirelength\s*=\s*[-0-9.]+,\s*CC\s*=\s*\K[-0-9.eE+]+' "$log_file" | tail -1)
    final_wirelength=$(grep -oP 'Final performance:\s*Wirelength\s*=\s*\K[-0-9.]+' "$log_file" | tail -1)
    final_CC=$(grep -oP 'Final performance:\s*Wirelength\s*=\s*[-0-9.]+,\s*CC\s*=\s*\K[-0-9.eE+]+' "$log_file" | tail -1)

    # Fallback for old logs
    initial_wirelength=${initial_wirelength:-$(grep -oP 'Initial total wirelength =\s*\K[-0-9.]+' "$log_file" | tail -1)}
    initial_CC=${initial_CC:-$(grep -oP 'Initial CC =\s*\K[-0-9.eE+]+' "$log_file" | tail -1)}

    # Safe defaults if parsing failed
    initial_wirelength=${initial_wirelength:-0}
    final_wirelength=${final_wirelength:-0}
    initial_CC=${initial_CC:-0}
    final_CC=${final_CC:-0}
    net_count=$(grep -oP 'Net count:\s*\K[0-9]+' "$log_file" | tail -1)
    io_count=$(grep -oP 'IO count:\s*\K[0-9]+' "$log_file" | tail -1)
    block_count=$(grep -oP 'Block count:\s*\K[0-9]+' "$log_file" | tail -1)

    # print them in the format:
    # round all values to 6 decimal places
    initial_wirelength=$(printf "%.6f" "$initial_wirelength")
    final_wirelength=$(printf "%.6f" "$final_wirelength")
    initial_CC=$(printf "%.6f" "$initial_CC")
    final_CC=$(printf "%.6f" "$final_CC")
    net_count=${net_count:-N/A}
    io_count=${io_count:-N/A}
    block_count=${block_count:-N/A}
    
    # Center align each field
    case_name_centered=$(center_text "$case_name" 9)
    initial_wl_centered=$(center_text "$initial_wirelength" 18)
    final_wl_centered=$(center_text "$final_wirelength" 16)
    initial_cc_centered=$(center_text "${initial_CC:-N/A}" 10)
    final_cc_centered=$(center_text "$final_CC" 8)
    net_count_centered=$(center_text "$net_count" 9)
    io_count_centered=$(center_text "$io_count" 8)
    block_count_centered=$(center_text "$block_count" 11)
    
    # | case_name | initial_wirelength | final_wirelength | initial_CC | final_CC |
    printf "| %s | %s | %s | %s | %s | %s | %s | %s |\n" "$case_name_centered" "$initial_wl_centered" "$final_wl_centered" "$initial_cc_centered" "$final_cc_centered" "$net_count_centered" "$io_count_centered" "$block_count_centered"

done

# print the lower boundary of the table
printf "|-----------|--------------------|------------------|------------|----------|-----------|----------|-------------|\n"