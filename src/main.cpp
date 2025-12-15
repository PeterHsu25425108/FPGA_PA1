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
    PROF_TIMER_ON(DEBUG_MAIN);
    solver.parser(infileName);
    PROF_TIMER_OFF("Parsing Time: ", PROFILING);
    DEBUG_MSG("Parser finished.", DEBUG_MAIN);

    DEBUG_MSG("Initializing solver...", DEBUG_MAIN);
    solver.initialize();
    DEBUG_MSG("Initialization finished.", DEBUG_MAIN);

    DEBUG_MSG("Starting Simulated Annealing optimization...", DEBUG_MAIN);
    solver.SA_optimize(10);
    DEBUG_MSG("SA optimization finished.", DEBUG_MAIN);

    DEBUG_MSG("Ouputting solution...", DEBUG_MAIN);
    solver.output(outfileName);
    DEBUG_MSG("Output finished.", DEBUG_MAIN);
    
    return 0;
}