#include "DEBUG.h"
#include <stack>
using namespace std;

// bool timer_on = false;
stack<clock_t> time_stack;
// clock_t start_time, end_time;
string msg;

void PROF_TIMER_ON(bool flag)
{
    if (flag && PROFILING)
    {
        clock_t start_time = clock();
        // timer_on = true;
        time_stack.push(start_time);
    }
}

void PROF_TIMER_OFF(const std::string& msg, bool flag)
{
    if (flag && PROFILING && /*timer_on*/!time_stack.empty())
    {
        clock_t end_time = clock();
        double elapsed_secs = double(end_time - time_stack.top()) / CLOCKS_PER_SEC;
        std::cout << "[PROFILE] " << msg << " took " << elapsed_secs << " seconds." << std::endl;
        time_stack.pop();
    }
}

// Debug message function
// void DEBUG_MSG(const std::string& msg, bool flag)
// {
//     if (flag && MASTER_DEBUG)
//     {
//         std::cout << "[DEBUG] " << msg << std::endl;
//     }
// }

// // overloaded ver for cstyle string
// void DEBUG_MSG(const char* msg, bool flag)
// {
//     if (flag && MASTER_DEBUG)
//     {
//         std::cout << "[DEBUG] " << msg << std::endl;
//     }
// }