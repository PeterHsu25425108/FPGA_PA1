#ifndef SOLVER_H
#define SOLVER_H
#include"DEBUG.h"
#include<vector>
#include<unordered_map>
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

struct IO{
    string name;
    int x;
    int y;
    // store the indicies of connected nets in the nets vector
    vector<int> connected_nets; 
    IO(): x(0), y(0) {}
    IO(string name, int x, int y) : name(name), x(x), y(y) {}
};

struct Net{
    string name;
    // store the indicies of connected blocks in the blocks vector
    vector<int> connected_blocks;
    // store the indicies of connected IOs in the ios vector
    vector<int> connected_ios;
    int x_min, x_max, y_min, y_max;
    Net(): x_min(0), x_max(0), y_min(0), y_max(0) {}
    Net(string name) : name(name), x_min(0), x_max(0), y_min(0), y_max(0) {}
};

class Solver{
public:
    void parser(string filename);
    Solver() {;}

private:
    int R, C;
    vector<Block> blocks;
    vector<IO> ios;
    vector<Net> nets;
    unordered_map<string, int> block_name_to_index;
    unordered_map<string, int> io_name_to_index;
    vector<vector<int>> U; // store the coverage U of each grid cell
    vector<vector<int>> block_occupancy; // store the index of the block occupying each grid cell, -1 if empty

    // SA parameters
    double T;
    double CC_linear, CC_square; // the linear and square sums for congestion cost calculation
};
#endif