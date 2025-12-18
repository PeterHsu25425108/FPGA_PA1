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
printf "| Case Name | Initial Wirelength | Final Wirelength | Initial CC | Final CC | Best Iter | Best Temp |\n"
printf "|-----------|--------------------|------------------|------------|----------|-----------|-----------|\n"

for testcase in testcases/*.txt; do
    case_name=$(basename "$testcase" .txt)
    # run ./placer case_name.txt result/case_name.out > case_name.log
    ./placer "$testcase" "result/${case_name}.out" > "${case_name}.log"

    # in the log file, search for "Final performance: Wirelength = [HPWL], CC = [Congestion Cost]"
    # and Initial total wirelength = [HPWL], Initial CC = [Congestion Cost](could be absent)
    log_file="${case_name}.log"
    initial_wirelength=$(grep -oP 'Initial total wirelength = \K[0-9]+' "$log_file")
    final_wirelength=$(grep -oP 'Final performance: Wirelength = \K[0-9]+' "$log_file")
    initial_CC=$(grep -oP 'Initial CC = \K[0-9.]+' "$log_file")
    final_CC=$(grep -oP 'CC = \K[0-9.]+' "$log_file" | tail -1)
    best_iter=$(grep -oP 'Best solution found at iteration \K[0-9]+' "$log_file")
    best_temp=$(grep -oP 'Temperature = \K[-0-9.eE]+' "$log_file")

    # print them in the format:
    # round all values to 6 decimal places
    initial_wirelength=$(printf "%.6f" "$initial_wirelength")
    final_wirelength=$(printf "%.6f" "$final_wirelength")
    initial_CC=$(printf "%.6f" "$initial_CC")
    final_CC=$(printf "%.6f" "$final_CC")
    best_iter=${best_iter:-N/A}
    if [ -n "$best_temp" ]; then
        # Use 6 significant digits for temperature
        best_temp=$(printf "%.6g" "$best_temp")
    else
        best_temp="N/A"
    fi
    
    # Center align each field
    case_name_centered=$(center_text "$case_name" 9)
    initial_wl_centered=$(center_text "$initial_wirelength" 18)
    final_wl_centered=$(center_text "$final_wirelength" 16)
    initial_cc_centered=$(center_text "${initial_CC:-N/A}" 10)
    final_cc_centered=$(center_text "$final_CC" 8)
    best_iter_centered=$(center_text "$best_iter" 9)
    best_temp_centered=$(center_text "$best_temp" 9)
    
    # | case_name | initial_wirelength | final_wirelength | initial_CC | final_CC |
    printf "| %s | %s | %s | %s | %s | %s | %s |\n" "$case_name_centered" "$initial_wl_centered" "$final_wl_centered" "$initial_cc_centered" "$final_cc_centered" "$best_iter_centered" "$best_temp_centered"

done

# print the lower boundary of the table
printf "|-----------|--------------------|------------------|------------|----------|-----------|-----------|\n"