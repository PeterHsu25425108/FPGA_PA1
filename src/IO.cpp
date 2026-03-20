#include<iostream>
#include"DEBUG.h"
#include"Solver.h"
#include<fstream>
#include<sstream>
#include<vector>
using namespace std;

#define DEBUG_PARSER 1
#define CHECK_PARSED_DATA 0
void Solver::parser(string filename){
    ifstream in_file(filename);
    string temp;
    stringstream ss;
    getline(in_file, temp);
    ss << temp;
    ss >> R >> C >> numLBs >> numIOs >> numNets;
    if(CHECK_PARSED_DATA)
        cout << R << " " << C << " " << numLBs << " " << numIOs << " " << numNets << endl;

    // parse logic blocks
    string blockName;
    for(int i = 0; i < numLBs; i++){
        getline(in_file, blockName);
        // add a new block to blocks vector
        blocks.push_back(Block(blockName));
        block_name_to_index[blockName] = i;
    }

    // parse IO blocks
    string ioName;
    double x, y;
    for(int i = 0; i < numIOs; i++){
        getline(in_file, temp);
        ss.clear();
        ss.str(temp);
        ss >> ioName >> x >> y;
        ios.push_back(IO(ioName, x, y));
        io_name_to_index[ioName] = i;
    }
    // output the content of blocks and ios in the same format as input file for checking
    if(CHECK_PARSED_DATA){
        for(auto& block : blocks){
            cout << block.name << "\n";
        }
        for(auto& io : ios){
            cout << io.name << " " << io.x << " " << io.y << "\n";
        }
    }

    // parse nets
    string netName;
    int degree;
    // either IO pin name or logic block name
    // vector<string> terminals;
    for(int i = 0; i < numNets; i++){
        getline(in_file, temp);
        ss.clear();
        ss.str(temp);
        ss >> netName >> degree;
        // add a new net to nets vector
        nets.push_back(Net(netName));

        // if(CHECK_PARSED_DATA)
        //     cout << netName << " " << degree << " ";

        for(int j = 0; j < degree; j++){
            string terminal;
            ss >> terminal;
            // terminals.push_back(terminal);
            // check if terminal is a logic block or an IO
            if(block_name_to_index.find(terminal) != block_name_to_index.end()){
                int block_index = block_name_to_index[terminal];
                nets[i].connected_blocks.push_back(block_index);
                blocks[block_index].connected_nets.push_back(i);
            } else if(io_name_to_index.find(terminal) != io_name_to_index.end()){
                int io_index = io_name_to_index[terminal];
                nets[i].connected_ios.push_back(io_index);
                ios[io_index].connected_nets.push_back(i);
            }
            else{
                cerr << "Error: terminal " << terminal << " not found in blocks or ios.\n";
            }

            // if(CHECK_PARSED_DATA)
            //     cout << terminal << (j == degree - 1 ? "\n" : " ");
        }

        // if(CHECK_PARSED_DATA)
        // {
        //     cout << netName << " " << degree << " ";
        //     for(auto t: terminals)
        //         cout << t << " ";
        //     cout << endl;
        // }
        // terminals.clear();
    }

    // output the content of nets in the same format as input file for checking
    if(CHECK_PARSED_DATA){
        for(auto& net : nets){
            cout << net.name << " " << net.connected_blocks.size() + net.connected_ios.size() << " ";
            for(auto b_index : net.connected_blocks){
                cout << blocks[b_index].name << " ";
            }
            for(auto io_index : net.connected_ios){
                cout << ios[io_index].name << " ";
            }
            cout << "\n";
        }
    }
    in_file.close();
}

#define DEBUG_OUTPUT 1
#define DEBUG_FINAL_PERFORMANCE 1
void Solver::output(string filename, bool prt_perf){
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