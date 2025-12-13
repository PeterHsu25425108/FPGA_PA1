#include"DEBUG.h"
#include"Solver.h"
#include<fstream>
#include<sstream>
#include<vector>
#include<cmath>
using namespace std;

// Assign initial positions to blocks and calculate initial cost
// initialize the grid and SA parameters
// calculate initial nets bounding boxes and total_wirelength
#define DEBUG_INITIALIZE 1
void Solver::initialize(){
    // initialize grid coverage U and block occupancy
    DEBUG_MSG("Received grid size: R=" + to_string(R) + ", C=" + to_string(C), DEBUG_INITIALIZE);
    DEBUG_MSG("Initializing grid and block occupancy...", DEBUG_INITIALIZE);
    U.resize(C, vector<int>(R, 0));
    block_occupancy.resize(C, vector<int>(R, -1)); // -1 indicates empty cell
    DEBUG_MSG("Grid and block occupancy initialized.", DEBUG_INITIALIZE);

    T = 1000.0; // initial temperature
    CC_linear = 0.0;
    CC_square = 0.0;
    total_wirelength = 0;

    // assign initial random positions to blocks within the grid
    
    // For simplicity, we place blocks in the grid sequentially
    int block_index = 0;
    for(int x = 0; x < C; ++x){
        for(int y = 0; y < R; ++y){
            if(block_index < blocks.size()){
                blocks[block_index].x = x;
                blocks[block_index].y = y;
                // initialize the values of block_occupancy
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
        // initialize bounding box
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

        // calculate total_wirelength for this net
        total_wirelength += (net.x_max - net.x_min) + (net.y_max - net.y_min);
    }

    // calculate the values of U
    for(auto &net : nets){
        // TODO: net bounding box may have non-integer coordinates due to IOs, need to 
        // change the below loop bond for x and y to handle that case
        int x_start, x_stop, y_start, y_end;
        // x_start and y_start: ceiling
        x_start = static_cast<int>(ceil(net.x_min));
        y_start = static_cast<int>(ceil(net.y_min));

        // For each cell in the bounding box of the net, increment U
        for(int x = x_start; x < net.x_max; ++x){
            for(int y = y_start; y < net.y_max; ++y){
                bool x_is_int = (x == static_cast<int>(x));
                bool y_is_int = (y == static_cast<int>(y));
                bool on_right_border = (x_is_int && x == C);
                bool on_top_border = (y_is_int && y == R);

                // if(x_is_int && y_is_int && !on_right_border && !on_top_border)
                U[x][y] += 1;
            }
        }
    }

    // calculate initial congestion cost components CC_linear and CC_square

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

    double CC_init = C*R * CC_square/(CC_linear * CC_linear);

    DEBUG_MSG("Initial total wirelength: " + to_string(total_wirelength), DEBUG_INITIALIZE);
    DEBUG_MSG("Initial CC = " + to_string(CC_init), DEBUG_INITIALIZE);

    // TODO: calculate initial total cost and update best_block_positions
    // total_cost = total_wirelength + alpha * CC_linear + beta * CC_square;

    best_block_positions.clear();
    for(auto &blk : blocks){
        best_block_positions.push_back(make_tuple(blk.x, blk.y, blk.name));
    }
}

void Solver::output(string filename){
    ofstream ofs(filename);
    if(!ofs.is_open()){
        cerr << "Error: Cannot open output file " << filename << endl;
        return;
    }

    for(auto &pos : best_block_positions){
        int x = get<0>(pos);
        int y = get<1>(pos);
        string name = get<2>(pos);
        stringstream ss;
        ss << name << " " << x << " " << y << "\n";
        ofs << ss.str();
    }
    ofs.close();

}