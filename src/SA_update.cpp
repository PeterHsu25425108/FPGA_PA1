#include"DEBUG.h"
#include"Solver.h"
#include<vector>
#include<unordered_map>
#include<unordered_set>
#include<algorithm>
#include<cmath>
using namespace std;

#define DEBUG_PERTURB 1
// perform perturbation: move a block to a new site OR swap two blocks
bool Solver::perturb(int block1_idx, int new_x, int new_y, int& acceptCount, long long int iter) {
    
    // --- STATIC BUFFERS (Optimization: Avoid re-allocation) ---
    static vector<pair<int, bool>> affected_nets; // net_id, block1_is_in_net
    static vector<NetDiff> net_diffs;
    affected_nets.clear();
    net_diffs.clear();

    // 1. Identify Blocks and Coordinates
    int block2_idx = block_occupancy[new_x][new_y]; // -1 if empty
    int b1_old_x = blocks[block1_idx].x;
    int b1_old_y = blocks[block1_idx].y;

    // Target coordinates for Block 2 (it moves to Block 1's old pos if swap)
    int b2_new_x = b1_old_x;
    int b2_new_y = b1_old_y;

    // 2. Collect Affected Nets (Uniquely)
    const vector<int>& n1 = blocks[block1_idx].connected_nets;
    for (int net_id : n1) {
        affected_nets.push_back(make_pair(net_id, true)); // block1 is in this net
    }

    // Pre-compute nets in both blocks for fast filtering
    unordered_set<int> nets_in_both;
    if (block2_idx != -1) {
        unordered_set<int> n1_set(n1.begin(), n1.end());
        const vector<int>& n2 = blocks[block2_idx].connected_nets;
        for (int net_id : n2) {
            if (n1_set.count(net_id)) {
                nets_in_both.insert(net_id);
            }
            affected_nets.push_back(make_pair(net_id, false)); // block1 may not be in this net
        }
    }

    // Remove nets that contain both block1 and block2 (bounding box won't change on swap)
    if (!nets_in_both.empty()) {
        affected_nets.erase(
            remove_if(affected_nets.begin(), affected_nets.end(),
                [&nets_in_both](const pair<int, bool>& net_pair) {
                    return nets_in_both.count(net_pair.first) > 0;
                }),
            affected_nets.end()
        );
    }

    // 3. Calculate Proposed Changes (NetDiffs)
    double delta_HPWL = 0;

    for (const auto& net_pair : affected_nets) {
        int net_idx = net_pair.first;
        bool block1_is_in_net = net_pair.second;
        NetDiff diff;
        // Calculate the hypothetical new box without modifying the actual Net struct yet
        bool changed = calc_net_update(net_idx, 
                                       block1_idx, new_x, new_y, 
                                       block2_idx, b2_new_x, b2_new_y, 
                                       diff, block1_is_in_net);
        if (changed) {
            net_diffs.push_back(diff);
            // HPWL = (xmax - xmin) + (ymax - ymin)
            double old_hpwl = (diff.old_x_max - diff.old_x_min) + (diff.old_y_max - diff.old_y_min);
            double new_hpwl = (diff.new_x_max - diff.new_x_min) + (diff.new_y_max - diff.new_y_min);
            delta_HPWL += (new_hpwl - old_hpwl);
        }
    }

    // 4. Update Grid and Global Scores (Forward)
    // This updates U, CC_linear, and CC_square in place
    update_congestion_map(net_diffs, false); 

    // 5. Calculate New Cost
    double curr_wirelength = prev_wirelength + delta_HPWL;
    
    // Calculate CC using the updated globals
    double curr_CC = 0;
    if (CC_linear > 1e-9) {
        curr_CC = (double)(C * R) * CC_square / (CC_linear * CC_linear);
    }

    // Cost Function
    // Uses raw delta based on your original loop setup
    double delta_Cost = 100*initialTemp* ((curr_wirelength - prev_wirelength)/prev_wirelength + (curr_CC - prev_CC)/prev_CC); 
    // double delta_Cost = 10*initialTemp* ((curr_wirelength - prev_wirelength) + (curr_CC - prev_CC) * prev_wirelength/prev_CC); 
    // double delta_Cost = 100*initialTemp* (curr_wirelength * curr_CC -prev_wirelength * prev_CC);

    // 6. Acceptance Criteria
    bool accept = false;
    if (delta_Cost < 0) {
        accept = true;
    } else {
        double r = (double)rand() / RAND_MAX;
        if (r < exp(-delta_Cost / T)) {
            DEBUG_MSG("Accepted uphill move with probability " + to_string(exp(-delta_Cost / T)), DEBUG_PERTURB);
            accept = true;
        }
    }

    // 7. Commit or Rollback
    if (accept) {
        DEBUG_MSG("Perturb accepted: ΔWirelength = " + to_string(curr_wirelength - prev_wirelength) +
                  ", ΔCC = " + to_string(curr_CC - prev_CC) +
                  ", ΔCost = " + to_string(delta_Cost), DEBUG_PERTURB);
        acceptCount++;
        // COMMIT:
        // A. Update Net Structs with the new boxes we calculated
        for (const auto& diff : net_diffs) {
            Net &net = nets[diff.net_index];
            net.x_min = diff.new_x_min; net.x_max = diff.new_x_max;
            net.y_min = diff.new_y_min; net.y_max = diff.new_y_max;
        }

        // B. Update Block Coordinates & Occupancy Grid
        // Move Block 1
        blocks[block1_idx].x = new_x;
        blocks[block1_idx].y = new_y;
        
        // Move Block 2 (if exists)
        if (block2_idx != -1) {
            blocks[block2_idx].x = b2_new_x;
            blocks[block2_idx].y = b2_new_y;
            block_occupancy[b1_old_x][b1_old_y] = block2_idx; 
        } else {
            block_occupancy[b1_old_x][b1_old_y] = -1; 
        }
        block_occupancy[new_x][new_y] = block1_idx; 

        // C. Update Global Costs
        prev_wirelength = curr_wirelength;
        prev_CC = curr_CC;
        DEBUG_MSG("Accepted move: New Wirelength = " + to_string(prev_wirelength) + ", New CC = " + to_string(prev_CC), DEBUG_PERTURB);

        // update best_block_positions if either wirelength or CC improved
        // and none of them are worse than before
        if(curr_wirelength < total_wirelength && curr_CC < CC){
            total_wirelength = curr_wirelength;
            CC = curr_CC;
            best_block_positions.clear();
            for(auto &blk : blocks){
                best_block_positions.push_back(make_tuple(blk.x, blk.y, blk.name));
            }
            best_sol_iter = iter;
            best_Temp = T;
        }

        return true;

    } else {
        DEBUG_MSG("Perturb rejected", DEBUG_PERTURB);
        // ROLLBACK:
        // A. Revert Grid and Global CC Scores
        update_congestion_map(net_diffs, true); // true = rollback

        // B. Revert Global Variables (prev_wirelength and prev_CC remain unchanged)
        // No need to touch Net structs or Blocks because we never wrote to them!
        
        return false;
    }
}

