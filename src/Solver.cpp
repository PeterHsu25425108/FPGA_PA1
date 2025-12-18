#include"DEBUG.h"
#include"Solver.h"
#include<fstream>
#include<sstream>
#include<vector>
#include<cmath>
#include<algorithm>
using namespace std;

double coolRate(double acceptRate)
{
    if(acceptRate > 0.95)
        return 0.9;
    else if(acceptRate > 0.8)
        return 0.99;
    else if(acceptRate > 0.15)
        return 0.99;
    else
        return 0.9;
}

#define DEBUG_SA 1
void Solver::SA_optimize(int max_iterations){

    long long int iter = 0;
    int changeTempIter = 5000; // number of iterations before changing temperature
    double coolingRate = 0.95; // cooling rate for temperature
    int acceptCount = 0; // count of consecutive rejections within current temperature
    
    
    T = initialTemp;
    while(true){
        // early stop mechanism
        prog_end_time = clock();
        double elapsed_secs = double(prog_end_time - prog_start_time) / CLOCKS_PER_SEC;
        if(elapsed_secs > 235){ // 235 seconds
            DEBUG_MSG("Early stopping SA due to time limit.", DEBUG_SA);
            break;
        }

        iter++;
        PROF_TIMER_ON(DEBUG_SA);
        // pertubation
        // pick a random block and a random target position
        int block_idx = rand() % numLBs;
        int new_x = rand() % C;
        bool same = true;
        while(new_x == blocks[block_idx].x) // ensure new_x is different
        {
            new_x = rand() % C;
            same = false;
        }

        int new_y = rand() % R;
        while(new_y == blocks[block_idx].y && same) // ensure new_y is different
            new_y = rand() % R;
        
        // apply perturbation
        bool accept_perturb = perturb(block_idx, new_x, new_y, acceptCount, iter);

        // After every changeTempIter iterations, update temperature
        if(iter % changeTempIter == 0){
            double acceptRate = static_cast<double>(acceptCount) / changeTempIter;
            coolingRate = coolRate(acceptRate);
            T *= coolingRate;
            acceptCount = 0; // reset accept count for next temperature phase
        }
        DEBUG_MSG("wirelength: " + to_string(total_wirelength) + ", CC: " + to_string(CC) + ", T: " + to_string(T), DEBUG_SA);
        PROF_TIMER_OFF("Iteration " + to_string(iter), DEBUG_SA);

        // Termination conditions
        if(max_iterations != -1 && iter >= max_iterations){
            break;
        }
        if(T < 1e-3){ // temperature threshold
            break;
        }
    }
}

// Assign initial positions to blocks and calculate initial cost
#define DEBUG_INITIALIZE 1
void Solver::initialize(){
    DEBUG_MSG("Received grid size: R=" + to_string(R) + ", C=" + to_string(C), DEBUG_INITIALIZE);
    DEBUG_MSG("Initializing grid and block occupancy...", DEBUG_INITIALIZE);
    U.resize(C, vector<int>(R, 0));
    block_occupancy.resize(C, vector<int>(R, -1)); // -1 indicates empty cell
    DEBUG_MSG("Grid and block occupancy initialized.", DEBUG_INITIALIZE);

    T = 1000.0; // initial temperature
    CC_linear = 0.0;
    CC_square = 0.0;
    prev_wirelength = 0;

    // assign initial random positions to blocks within the grid
    int block_index = 0;
    for(int x = 0; x < C; ++x){
        for(int y = 0; y < R; ++y){
            if(block_index < blocks.size()){
                blocks[block_index].x = x;
                blocks[block_index].y = y;
                block_occupancy[x][y] = block_index;
                ++block_index;
            }
            else{
                break;
            }
        }
        if(block_index >= blocks.size()){
            break;
        }
    }

    // calculate initial nets bounding boxes and total_wirelength
    for(auto &net : nets){
        net.x_min = C; net.x_max = 0;
        net.y_min = R; net.y_max = 0;

        // update bounding box based on connected blocks
        for(auto block_idx : net.connected_blocks){
            Block &blk = blocks[block_idx];
            if((double)blk.x < net.x_min) net.x_min = blk.x;
            if((double)blk.x+1 > net.x_max) net.x_max = blk.x+1;
            if((double)blk.y < net.y_min) net.y_min = blk.y;
            if((double)blk.y+1 > net.y_max) net.y_max = blk.y+1;
        }

        // update bounding box based on connected IOs
        for(auto io_idx : net.connected_ios){
            IO &io = ios[io_idx];
            if(io.x < net.x_min) net.x_min = io.x;
            if(io.x > net.x_max) net.x_max = io.x;
            if(io.y < net.y_min) net.y_min = io.y;
            if(io.y > net.y_max) net.y_max = io.y;
        }

        prev_wirelength += (net.x_max - net.x_min) + (net.y_max - net.y_min);
    }
    total_wirelength = prev_wirelength;

    // calculate the values of U
    for(auto &net : nets){
        int x_start = static_cast<int>(ceil(net.x_min));
        int y_start = static_cast<int>(ceil(net.y_min));

        for(int x = x_start; x < net.x_max; ++x){
            for(int y = y_start; y < net.y_max; ++y){
                U[x][y] += 1;
            }
        }
    }

    // calculate initial congestion cost components
    for(double x = 0; x < C; ++x){
        for(double y = 0; y < R; ++y){
            CC_linear += U[x][y];
            CC_square += U[x][y] * U[x][y];
        }
    }
    if(CC_linear < 1e-6) 
    {
        cerr << "CC_linear is too small (" << CC_linear << "), may cause division by zero." << endl;
        exit(1);
    }
    prev_CC = C*R * CC_square/(CC_linear * CC_linear);
    CC = prev_CC;

    // DEBUG_MSG("Initial total wirelength: " + to_string(prev_wirelength), DEBUG_INITIALIZE);
    cout << "Initial total wirelength = " << prev_wirelength << ", ";
    // DEBUG_MSG("Initial CC = " + to_string(prev_CC), DEBUG_INITIALIZE);
    cout << "Initial CC = " << prev_CC << endl;

    best_block_positions.clear();
    for(auto &blk : blocks){
        best_block_positions.push_back(make_tuple(blk.x, blk.y, blk.name));
    }

    // // print the bounding box for net_1623
    // string net_name = "net_1623";
    // for(auto &net : nets){
    //     if(net.name == net_name){
    //         DEBUG_MSG("Bounding box for " + net.name + ": x_min=" + to_string(net.x_min) + ", x_max=" + to_string(net.x_max) +
    //                   ", y_min=" + to_string(net.y_min) + ", y_max=" + to_string(net.y_max), DEBUG_INITIALIZE);
    //         // print all its connected blocks and IOs
    //         DEBUG_MSG("Connected Blocks:", DEBUG_INITIALIZE);
    //         for(auto blk_idx : net.connected_blocks){
    //             Block &blk = blocks[blk_idx];
    //             DEBUG_MSG("  Block " + blk.name + " at (" + to_string(blk.x) + "," + to_string(blk.y) + ")", DEBUG_INITIALIZE);
    //         }
    //         DEBUG_MSG("Connected IOs:", DEBUG_INITIALIZE);
    //         for(auto io_idx : net.connected_ios){
    //             IO &io = ios[io_idx];
    //             DEBUG_MSG("  IO " + io.name + " at (" + to_string(io.x) + "," + to_string(io.y) + ")", DEBUG_INITIALIZE);
    //         }
    //         break;
    //     }
    // }
}

// --- INCREMENTAL HELPERS IMPLEMENTATION ---

// Helper: Calculate new bounding box. 
// Fully Optimized: Uses Anchor Checks to avoid O(N) scans on inward moves.
#define ENABLE_SPEEDUP 1
#define CHECK_CORRECTNESS 0
bool Solver::calc_net_update(int net_idx, int b1_idx, int b1_new_x, int b1_new_y,
                             int b2_idx, int b2_new_x, int b2_new_y, 
                             NetDiff &diff, bool block1_is_in_net) 
{
    Net &net = nets[net_idx];
    diff.net_index = net_idx;

    DEBUG_MSG("Calculating net update for net " + net.name, DEBUG_SA);

    // 1. Snapshot Old State
    diff.old_x_min = net.x_min; diff.old_x_max = net.x_max;
    diff.old_y_min = net.y_min; diff.old_y_max = net.y_max;

    // Initialize New State with Old State
    diff.new_x_min = net.x_min; diff.new_x_max = net.x_max;
    diff.new_y_min = net.y_min; diff.new_y_max = net.y_max;

    // Pre-fetch positions (casting to double for consistent comparison)
    // Note: Blocks have width 1.0, so Max = x + 1.0
    double b1_old_x = (double)blocks[b1_idx].x;
    double b1_old_y = (double)blocks[b1_idx].y;
    double b1_next_x = (double)b1_new_x;
    double b1_next_y = (double)b1_new_y;

    double b2_old_x = 0, b2_old_y = 0;
    double b2_next_x = 0, b2_next_y = 0;
    bool has_b2 = (b2_idx != -1);

    if (has_b2) {
        b2_old_x = (double)blocks[b2_idx].x;
        b2_old_y = (double)blocks[b2_idx].y;
        b2_next_x = (double)b2_new_x;
        b2_next_y = (double)b2_new_y;
    }

    
    double next_block_x = (block1_is_in_net) ? b1_next_x : b2_next_x;
    double next_block_y = (block1_is_in_net) ? b1_next_y : b2_next_y;
    double old_block_x = (block1_is_in_net) ? b1_old_x : b2_old_x;
    double old_block_y = (block1_is_in_net) ? b1_old_y : b2_old_y;

    // Flags to trigger full recalculation for an axis
    bool recalc_x = false;
    bool recalc_y = false;

    bool on_xmin_boundary, on_xmax_boundary, on_ymin_boundary, on_ymax_boundary;

    // --- X-AXIS LOGIC ---
    
    // 1. Check for Extensions (Move Outward)
    // if (b1_next_x < diff.new_x_min) diff.new_x_min = b1_next_x;
    // if (b1_next_x + 1.0 > diff.new_x_max) diff.new_x_max = b1_next_x + 1.0;
    
    // if (has_b2) {
    //     if (b2_next_x < diff.new_x_min) diff.new_x_min = b2_next_x;
    //     if (b2_next_x + 1.0 > diff.new_x_max) diff.new_x_max = b2_next_x + 1.0;
    // }

    // DEBUG_MSG("diff.new_x_min after extension: " + to_string(diff.new_x_min), DEBUG_SA);
    // DEBUG_MSG("diff.new_x_max after extension: " + to_string(diff.new_x_max), DEBUG_SA);


    // goal: to correctly set diff.new_x_min, diff.new_x_max, recalc_x
    if(ENABLE_SPEEDUP){
        
        on_xmin_boundary = old_block_x == diff.old_x_min;
        on_xmax_boundary = old_block_x + 1.0 == diff.old_x_max;
        
        if(on_xmin_boundary && on_xmax_boundary){
            // moving block was the only anchor on both sides: must recalc
            recalc_x = true;
        }
        else if(on_xmin_boundary){// Check Min Boundary Break
            if(next_block_x < diff.old_x_min)
                diff.new_x_min = next_block_x;
            else recalc_x = true;
        }
        else if(on_xmax_boundary){// check Max Boundary Break
            if(next_block_x + 1.0 > diff.old_x_max)
                diff.new_x_max = next_block_x + 1.0;
            else recalc_x = true;
        }
        else // not on any x boundary: just check extensions
        {
            if(next_block_x < diff.old_x_min)
                diff.new_x_min = next_block_x;
            else if(next_block_x + 1.0 > diff.old_x_max)
                diff.new_x_max = next_block_x + 1.0;
        }

       
        // --- Y-AXIS LOGIC (Mirror of X) ---

        on_ymin_boundary = old_block_y == diff.old_y_min;
        on_ymax_boundary = old_block_y + 1.0 == diff.old_y_max;
        if(on_ymin_boundary && on_ymax_boundary){
            // moving block was the only anchor on both sides: must recalc
            recalc_y = true;
        }
        else if(on_ymin_boundary){// Check Min Boundary Break
            if(next_block_y < diff.old_y_min)
                diff.new_y_min = next_block_y;
            else recalc_y = true;
        }
        else if(on_ymax_boundary){// check Max Boundary Break
            if(next_block_y + 1.0 > diff.old_y_max)
                diff.new_y_max = next_block_y + 1.0;
            else recalc_y = true;
        }
        else // not on any y boundary: just check extensions
        {
            if(next_block_y < diff.old_y_min)
                diff.new_y_min = next_block_y;
            else if(next_block_y + 1.0 > diff.old_y_max)
                diff.new_y_max = next_block_y + 1.0;
        }
        
        // 1. Extensions
        // if (b1_next_y < diff.new_y_min) diff.new_y_min = b1_next_y;
        // if (b1_next_y + 1.0 > diff.new_y_max) diff.new_y_max = b1_next_y + 1.0;

        // if (has_b2) {
        //     if (b2_next_y < diff.new_y_min) diff.new_y_min = b2_next_y;
        //     if (b2_next_y + 1.0 > diff.new_y_max) diff.new_y_max = b2_next_y + 1.0;
        // }

        // DEBUG_MSG("diff.new_y_min after extension: " + to_string(diff.new_y_min), DEBUG_SA);
        // DEBUG_MSG("diff.new_y_max after extension: " + to_string(diff.new_y_max), DEBUG_SA);

        // // 2. Contractions
        // on_ymin_boundary = (b1_old_y == diff.old_y_min) || (has_b2 && b2_old_y == diff.old_y_min);
        // if (on_ymin_boundary) {
        //     bool anchor_found = false;
        //     if (b1_next_y == diff.old_y_min) anchor_found = true;
        //     else if (has_b2 && b2_next_y == diff.old_y_min) anchor_found = true;
            
        //     if (!anchor_found) {
        //         for (int blk_idx : net.connected_blocks) {
        //             if (blk_idx == b1_idx || (has_b2 && blk_idx == b2_idx)) continue;
        //             if ((double)blocks[blk_idx].y == diff.old_y_min) { anchor_found = true; break; }
        //         }
        //     }
        //     if (!anchor_found) {
        //         for (int io_idx : net.connected_ios) {
        //             if (ios[io_idx].y == diff.old_y_min) { anchor_found = true; break; }
        //         }
        //     }
        //     if (!anchor_found) recalc_y = true;
        // }

        // if (!recalc_y) {
        //     on_ymax_boundary = (b1_old_y + 1.0 == diff.old_y_max) || (has_b2 && b2_old_y + 1.0 == diff.old_y_max);
        //     if (on_ymax_boundary) {
        //         bool anchor_found = false;
        //         if (b1_next_y + 1.0 == diff.old_y_max) anchor_found = true;
        //         else if (has_b2 && b2_next_y + 1.0 == diff.old_y_max) anchor_found = true;
                
        //         if (!anchor_found) {
        //             for (int blk_idx : net.connected_blocks) {
        //                 if (blk_idx == b1_idx || (has_b2 && blk_idx == b2_idx)) continue;
        //                 if ((double)blocks[blk_idx].y + 1.0 == diff.old_y_max) { anchor_found = true; break; }
        //             }
        //         }
        //         if (!anchor_found) {
        //             for (int io_idx : net.connected_ios) {
        //                 if (ios[io_idx].y == diff.old_y_max) { anchor_found = true; break; }
        //             }
        //         }
        //         if (!anchor_found) recalc_y = true;
        //     }
        // }
    }else{
        // If speedup disabled, always recalc both axes
        recalc_x = true;
        recalc_y = true;
    }

    // --- FINAL RECALCULATION (Only if Anchor Checks Failed) ---
    // Separated per-axis to avoid mixing partial results.
    // --- FINAL RECALCULATION (Only if Anchor Checks Failed) ---
    if (recalc_x || recalc_y) {
        double temp_xmin = (recalc_x) ? 1e9 : diff.new_x_min;
        double temp_xmax = (recalc_x) ? -1e9 : diff.new_x_max;
        double temp_ymin = (recalc_y) ? 1e9 : diff.new_y_min;
        double temp_ymax = (recalc_y) ? -1e9 : diff.new_y_max;

        // Scan Blocks
        for (int blk_idx : net.connected_blocks) {
            double bx, by;
            if (blk_idx == b1_idx) { bx = b1_next_x; by = b1_next_y; }
            else if (has_b2 && blk_idx == b2_idx) { bx = b2_next_x; by = b2_next_y; }
            else { bx = (double)blocks[blk_idx].x; by = (double)blocks[blk_idx].y; }

            if (recalc_x) {
                if (bx < temp_xmin) temp_xmin = bx;
                if (bx + 1.0 > temp_xmax) temp_xmax = bx + 1.0;
            }
            if (recalc_y) {
                if (by < temp_ymin) temp_ymin = by;
                if (by + 1.0 > temp_ymax) temp_ymax = by + 1.0;
            }
        }

        // Scan IOs
        for (int io_idx : net.connected_ios) {
            double ix = ios[io_idx].x;
            double iy = ios[io_idx].y;
            if (recalc_x) {
                if (ix < temp_xmin) temp_xmin = ix;
                if (ix > temp_xmax) temp_xmax = ix;
            }
            if (recalc_y) {
                if (iy < temp_ymin) temp_ymin = iy;
                if (iy > temp_ymax) temp_ymax = iy;
            }
        }

        if (recalc_x) { diff.new_x_min = temp_xmin; diff.new_x_max = temp_xmax; }
        if (recalc_y) { diff.new_y_min = temp_ymin; diff.new_y_max = temp_ymax; }
    }

    // if recalc_x and recalc_y are both false, perform a scan as the above block to verify correctness
    #if CHECK_CORRECTNESS
    {
        double verify_xmin = 1e9, verify_xmax = -1e9;
        double verify_ymin = 1e9, verify_ymax = -1e9;
        for (int blk_idx : net.connected_blocks) {
            double bx = (blk_idx == b1_idx) ? b1_next_x : (has_b2 && blk_idx == b2_idx) ? b2_next_x : (double)blocks[blk_idx].x;
            double by = (blk_idx == b1_idx) ? b1_next_y : (has_b2 && blk_idx == b2_idx) ? b2_next_y : (double)blocks[blk_idx].y;

            if (bx < verify_xmin) verify_xmin = bx;
            if (bx + 1.0 > verify_xmax) verify_xmax = bx + 1.0;
            if (by < verify_ymin) verify_ymin = by;
            if (by + 1.0 > verify_ymax) verify_ymax = by + 1.0;
        }
        for (int io_idx : net.connected_ios) {
            double ix = ios[io_idx].x;
            double iy = ios[io_idx].y;
            if (ix < verify_xmin) verify_xmin = ix;
            if (ix > verify_xmax) verify_xmax = ix;
            if (iy < verify_ymin) verify_ymin = iy;
            if (iy > verify_ymax) verify_ymax = iy;
        }
        // Compare
        if (fabs(verify_xmin - diff.new_x_min) > 1e-6 || fabs(verify_xmax - diff.new_x_max) > 1e-6 ||
            fabs(verify_ymin - diff.new_y_min) > 1e-6 || fabs(verify_ymax - diff.new_y_max) > 1e-6) {
            cout << "Error in calc_net_update for net " << net.name << ": Mismatch in bounding box calculation!" << endl;
            // Output recalc_x and recalc_y status
            if(recalc_x) cout << "Recalculated X-axis." << endl;
            else cout << "X-axis stayed the same." << endl;
            if(recalc_y) cout << "Recalculated Y-axis." << endl;
            else cout << "Y-axis stayed the same." << endl;
            // Ouput broken flags
            if(on_xmin_boundary) cout << "The block is on X Min boundary." << endl;
            if(on_xmax_boundary) cout << "The block is on X Max boundary." << endl;
            if(on_ymin_boundary) cout << "The block is on Y Min boundary." << endl;
            if(on_ymax_boundary) cout << "The block is on Y Max boundary." << endl;

            cout << "Old Box: x_min=" << diff.old_x_min << ", x_max=" << diff.old_x_max
                 << ", y_min=" << diff.old_y_min << ", y_max=" << diff.old_y_max << endl;
            // List all other block and IO positions for debugging
            cout << "Connected Blocks:" << endl;
            for (int blk_idx : net.connected_blocks) {
                if(blk_idx == b1_idx /*&& block1_is_in_net*/){
                    double bx = b1_next_x;
                    double by = b1_next_y;
                    cout << "  Block 1 , originally at (" << (int)b1_old_x << "," << (int)b1_old_y << ") [Moved]"<< endl;
                    continue;
                }
                else if(has_b2 && blk_idx == b2_idx /*&& !block1_is_in_net*/){
                    double bx = b2_next_x;
                    double by = b2_next_y;
                    cout << "  Block 2 , originally at (" << (int)b2_old_x << "," << (int)b2_old_y << ") [Moved]" << endl;
                    continue;
                }
                double bx = (double)blocks[blk_idx].x;
                double by = (double)blocks[blk_idx].y;
                cout << "  Block "<< blocks[blk_idx].name << " at (" << (int)bx << "," << (int)by << ")" << endl;
            }
            cout << "Connected IOs:" << endl;
            for (int io_idx : net.connected_ios) {
                cout << "  IO " << ios[io_idx].name << " at (" << (int)ios[io_idx].x << "," << (int)ios[io_idx].y << ")" << endl;
            }

            if (has_b2) {
                cout << "Swapping Block 1 at (" << (int)b1_old_x << "," << (int)b1_old_y << ") with Block 2 at ("
                     << (int)b2_old_x << "," << (int)b2_old_y << ")" << endl;
            }else{
                cout << "Block 1's original pos: (" << (int)b1_old_x << "," << (int)b1_old_y << "), "
                     << "New pos: (" << b1_new_x << "," << b1_new_y << ")" << endl;
            }

            cout << "Calculated: x_min=" << diff.new_x_min << ", x_max=" << diff.new_x_max
                 << ", y_min=" << diff.new_y_min << ", y_max=" << diff.new_y_max << endl;
            cout << "Verified:   x_min=" << verify_xmin << ", x_max=" << verify_xmax
                 << ", y_min=" << verify_ymin << ", y_max=" << verify_ymax << endl;
            exit(1);
        }
    }
    #endif

    // Return false if box didn't change (Optimization for calling function)
    if (diff.old_x_min == diff.new_x_min && diff.old_x_max == diff.new_x_max &&
        diff.old_y_min == diff.new_y_min && diff.old_y_max == diff.new_y_max) {
        return false;
    }

    return true;
}

void Solver::update_congestion_map(const vector<NetDiff>& updates, bool is_rollback) {
    for (const auto& diff : updates) {
        double x_min_sub, x_max_sub, y_min_sub, y_max_sub;
        double x_min_add, x_max_add, y_min_add, y_max_add;

        if (!is_rollback) {
            // Normal: Remove Old, Add New
            x_min_sub = diff.old_x_min; x_max_sub = diff.old_x_max;
            y_min_sub = diff.old_y_min; y_max_sub = diff.old_y_max;
            x_min_add = diff.new_x_min; x_max_add = diff.new_x_max;
            y_min_add = diff.new_y_min; y_max_add = diff.new_y_max;
        } else {
            // Rollback: Remove New, Add Old
            x_min_sub = diff.new_x_min; x_max_sub = diff.new_x_max;
            y_min_sub = diff.new_y_min; y_max_sub = diff.new_y_max;
            x_min_add = diff.old_x_min; x_max_add = diff.old_x_max;
            y_min_add = diff.old_y_min; y_max_add = diff.old_y_max;
        }

        // 1. Subtract
        int xs = (int)ceil(x_min_sub), xe = (int)x_max_sub;
        int ys = (int)ceil(y_min_sub), ye = (int)y_max_sub;
        
        for (int x = xs; x < xe; ++x) {
            for (int y = ys; y < ye; ++y) {
                CC_linear -= 1.0; 
                CC_square -= (2.0 * U[x][y] - 1.0); 
                U[x][y] -= 1;
            }
        }

        // 2. Add
        xs = (int)ceil(x_min_add); xe = (int)x_max_add;
        ys = (int)ceil(y_min_add); ye = (int)y_max_add;

        for (int x = xs; x < xe; ++x) {
            for (int y = ys; y < ye; ++y) {
                CC_linear += 1.0; 
                CC_square += (2.0 * U[x][y] + 1.0); 
                U[x][y] += 1;
            }
        }
    }
}