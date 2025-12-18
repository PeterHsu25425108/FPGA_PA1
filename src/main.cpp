#include<iostream>
#include"DEBUG.h"
#include"Solver.h"
using namespace std;
#define DEBUG_MAIN 1
#define PLOT_INIT 1

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

    // output the initial placement into a file for debugging
    // the file name is outfileBase_init.txt
    string outfileBase = outfileName.substr(0, outfileName.find_last_of('.'));
    string initOutfile = outfileBase + "_init.txt";
    DEBUG_MSG("Outputting initial placement to " + initOutfile, DEBUG_MAIN);
    solver.output(initOutfile);
    DEBUG_MSG("Initial placement output finished.", DEBUG_MAIN);

    DEBUG_MSG("Starting Simulated Annealing optimization...", DEBUG_MAIN);
    for(int i=0; i<5; ++i)
    {
        cout << "SA Optimization Round " << (i+1) << " ..." << endl;
        solver.SA_optimize();
        solver.setInitTemp(solver.getInitTemp() * 0.9);
    }
    DEBUG_MSG("SA optimization finished.", DEBUG_MAIN);

    DEBUG_MSG("Ouputting solution...", DEBUG_MAIN);
    solver.output(outfileName, true);
    DEBUG_MSG("Output finished.", DEBUG_MAIN);
    
    return 0;
}