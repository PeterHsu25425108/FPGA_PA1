#include<iostream>
#include"DEBUG.h"
#include"Solver.h"
using namespace std;
#define DEBUG_MAIN 1

void parser(string filename);

int main(int argc, char* argv[]) {
    string infileName = argv[1];
    string outfileName = argv[2];

    Solver solver;
    DEBUG_MSG("Starting parser...", DEBUG_MAIN);
    solver.parser(infileName);
    DEBUG_MSG("Parser finished.", DEBUG_MAIN);
    
    return 0;
}