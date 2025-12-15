#ifndef SOLVER_H
#define SOLVER_H
#include"DEBUG.h"
#include<vector>
#include<unordered_map>
#include<tuple>
#include<string>
#include<algorithm>
using namespace std;

struct Block{
    string name;
    int x;
    int y;
    // store the indicies of connected nets in the nets vector
    vector<int> connected_nets; 
    Block(): x(0), y(0) {}
    Block(string name) : name(name), x(0), y(0) {}
};

// IO coordinates can be non-integer values or right on the right or top border
struct IO{
    string name;
    double x;
    double y;
    // store the indicies of connected nets in the nets vector
    vector<int> connected_nets; 
    IO(): x(0), y(0) {}
    IO(string name, double x, double y) : name(name), x(x), y(y) {}
};

struct Net{
    string name;
    // store the indicies of connected blocks in the blocks vector
    vector<int> connected_blocks;
    // store the indicies of connected IOs in the ios vector
    vector<int> connected_ios;
    // bounding box coordinates
    double x_min, x_max, y_min, y_max;
    Net(): x_min(0), x_max(0), y_min(0), y_max(0) {}
    Net(string name) : name(name), x_min(0), x_max(0), y_min(0), y_max(0) {}
};

// NEW: Snapshot structure for incremental updates
struct NetDiff {
    int net_index;
    double old_x_min, old_x_max, old_y_min, old_y_max;
    double new_x_min, new_x_max, new_y_min, new_y_max;
};

class Solver{
public:
    void parser(string filename);
    Solver() {prog_start_time = clock();}

    // Assign initial positions to blocks and calculate initial cost
    void initialize();
    // output the best solution found
    void output(string filename);
    // perform simulated annealing to optimize block placement
    void SA_optimize(int max_iterations=-1);

    // perform perturbation: move a block to a new site
    bool perturb(int block1_idx, int new_x, int new_y, int& acceptCount);

private:
    double initialTemp = 800000.0;
    clock_t prog_start_time, prog_end_time;
    int R, C, numLBs, numIOs, numNets;
    vector<Block> blocks;
    vector<tuple<int, int, string>> best_block_positions; // (x, y, block_name)
    vector<IO> ios;
    vector<Net> nets;
    unordered_map<string, int> block_name_to_index;
    unordered_map<string, int> io_name_to_index;

    // indexing: [x][y] (the first dim is x-coordinate, which is column index)
    vector<vector<int>> U; // store the coverage U of each grid cell
    vector<vector<int>> block_occupancy; // store the index of the block occupying each grid cell, -1 if empty

    // SA parameters
    double T;
    double CC_linear, CC_square; // the linear and square sums for congestion cost calculation
    double prev_wirelength, prev_CC;
    // cost components
    double total_wirelength, CC;

    // --- INCREMENTAL HELPERS ---
    // Helper to calculate the new bounding box given a proposed move/swap
    bool calc_net_update(int net_idx, int b1_idx, int b1_new_x, int b1_new_y,
                         int b2_idx, int b2_new_x, int b2_new_y, 
                         NetDiff &diff, bool block1_is_in_net);

    // Helper to update U grid and global CC scores using the diffs
    void update_congestion_map(const vector<NetDiff>& updates, bool is_rollback);
};
#endif