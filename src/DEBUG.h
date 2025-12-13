#ifndef DEBUG_H
#define DEBUG_H
#include <iostream>
#include <cstring>
using namespace std;

// the master debug flag: 0 -> switch off all debug msg
#define MASTER_DEBUG 1
// profiling flag
#define PROFILING 1

void PROF_TIMER_ON(bool flag);
void PROF_TIMER_OFF(const std::string& msg, bool flag);
// void DEBUG_MSG(const std::string& msg, bool flag);
// void DEBUG_MSG(const char* msg, bool flag);
#define DEBUG_MSG(msg, flag) \
    do { \
        if (flag && MASTER_DEBUG) { \
            std::cout << "[DEBUG] " << msg << std::endl; \
        } \
    } while (0)

#endif
