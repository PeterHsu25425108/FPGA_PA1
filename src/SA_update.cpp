#include"DEBUG.h"
#include"Solver.h"
#include<vector>
#include<unordered_map>
#include<unordered_set>
#include<cmath>
using namespace std;

// perform perturbation: move a block to a new site
// return: accept perturbation or not
// if rejected, changes are rolled back
bool Solver::perturb(int block1_idx, int new_x, int new_y){
    // for rollback 
    // TODO: how to rollback U, and net bounding boxes?

    // record the old position of block1
    pair<int, int> prev_block1_pos = make_pair(blocks[block1_idx].x, blocks[block1_idx].y);
    double prev_CC_linear = CC_linear;;
    double prev_CC_square = CC_square;

    // check if the new position is occupied
    if(block_occupancy[new_x][new_y] == -1){
        // empty site, move the block

        // find all nets connected to this block, and preserve their old bounding boxes
        // so that we can rollback if needed
        vector<double> old_x_mins, old_x_maxs, old_y_mins, old_y_maxs;
        for(auto net_idx : blocks[block1_idx].connected_nets){
            Net &net = nets[net_idx];
            // preserve old bounding box
            old_x_mins.push_back(net.x_min);
            old_x_maxs.push_back(net.x_max);
            old_y_mins.push_back(net.y_min);
            old_y_maxs.push_back(net.y_max);
        }



    }
    else{
        // occupied site, swap the two blocks
        int block2_idx = block_occupancy[new_x][new_y];

        // record the old position of block2
        pair<int, int> prev_block2_pos = make_pair(blocks[block2_idx].x, blocks[block2_idx].y);

        // record the indices of the nets affected by the swap
        // aka the nets connected to either of the two blocks, but not both
        unordered_set<int> affected_nets;
        for(auto net_idx : blocks[block1_idx].connected_nets){
            affected_nets.insert(net_idx);
        }
        for(auto net_idx : blocks[block2_idx].connected_nets){
            if(affected_nets.find(net_idx) != affected_nets.end()){
                affected_nets.erase(net_idx);
            }
            else{
                affected_nets.insert(net_idx);
            }
        }

        // record old bounding boxes of affected nets
        vector<double> old_x_mins, old_x_maxs, old_y_mins, old_y_maxs;
        vector<int> affected_nets_vec(affected_nets.begin(), affected_nets.end());
        for(auto net_idx : affected_nets_vec){
            Net &net = nets[net_idx];
            // preserve old bounding box
            old_x_mins.push_back(net.x_min);
            old_x_maxs.push_back(net.x_max);
            old_y_mins.push_back(net.y_min);
            old_y_maxs.push_back(net.y_max);
        }
        
    }

    return false;
}