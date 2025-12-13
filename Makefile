CASENAME?=alu4
SRCDIR=src
OBJDIR=obj

# compiler settings 
CXX = g++
CXXFLAGS = -I ./include -std=c++11 -DPRINTTIME=true -DNDEBUG 
OPTFLAGS = -flto -funroll-loops -finline-functions -O3 -ffast-math
WARNINGS = -Wall -g #-pg

SRCS = $(wildcard $(SRCDIR)/*.cpp)
OBJS = $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.o,$(SRCS))
DEPS = $(patsubst $(SRCDIR)/%.cpp,$(OBJDIR)/%.d,$(SRCS))

TARGET = placer

all: $(TARGET)

$(OBJDIR):
	@mkdir $(OBJDIR)

$(TARGET): $(OBJS)
	$(CXX) $(WARNINGS) $(CXXFLAGS) $(OPTFLAGS) $^ -o $@

$(OBJDIR)/%.o: $(SRCDIR)/%.cpp | $(OBJDIR)
	$(CXX) $(WARNINGS) $(CXXFLAGS) $(OPTFLAGS) -MMD -MP -c $< -o $@

# Include generated dependencies (ignore if don't exist yet)
-include $(DEPS)

run: $(TARGET)
	./$(TARGET) testcases/$(CASENAME).txt result/$(CASENAME).out > $(CASENAME).log

check: $(TARGET)
	./checker testcases/$(CASENAME).txt $(CASENAME).out

run_val: $(TARGET)
	valgrind --leak-check=full --show-leak-kinds=all --log-file=$(CASENAME)_valgrind.log ./$(TARGET) testcases/$(CASENAME).txt $(CASENAME).out > $(CASENAME).log

clean:
	rm -f $(TARGET)
	rm -rf $(OBJDIR)

clean_txt:
	rm -f *.txt *.log
#	rm -rf results/*