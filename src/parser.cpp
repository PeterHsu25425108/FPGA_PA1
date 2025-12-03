#include<iostream>
#include"DEBUG.h"
#include<fstream>
#include<sstream>
#include<vector>
using namespace std;

#define DEBUG_PARSER 1
#define CHECK_PARSED_DATA 1
void parser(string filename){
    ifstream in_file(filename);
    string temp;
    stringstream ss;
    int R, C, numLBs, numIOs, numNets;
    getline(in_file, temp);
    ss << temp;
    ss >> R >> C >> numLBs >> numIOs >> numNets;
    if(CHECK_PARSED_DATA)
        cout << R << " " << C << " " << numLBs << " " << numIOs << " " << numNets << endl;

    // parse logic blocks
    string blockName;
    for(int i = 0; i < numLBs; i++){
       getline(in_file, blockName);
       if(CHECK_PARSED_DATA)
           cout << blockName << endl;
    }
    // parse IO blocks
    string ioName;
    double x, y;
    for(int i = 0; i < numIOs; i++){
        getline(in_file, temp);
        ss.clear();
        ss.str(temp);
        ss >> ioName >> x >> y;
        if(CHECK_PARSED_DATA)
            cout << ioName << " " << x << " " << y << endl;
    }

    // parse nets
    string netName;
    int degree;
    // either IO pin name or logic block name
    vector<string> terminals;
    for(int i = 0; i < numNets; i++){
        getline(in_file, temp);
        ss.clear();
        ss.str(temp);
        ss >> netName >> degree;
        for(int j = 0; j < degree; j++){
            string terminal;
            ss >> terminal;
            terminals.push_back(terminal);
        }

        if(CHECK_PARSED_DATA)
        {
            cout << netName << " " << degree << " ";
            for(auto t: terminals)
                cout << t << " ";
            cout << endl;
        }
        terminals.clear();
    }
    in_file.close();
}