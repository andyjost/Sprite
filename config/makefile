# Use this makefile to configure how Sprite builds Curry programs.  This file
# will be included after the following variables are defined:
#
#     FLAT_CURRY  - The list of .fcy files required for the program
#     MAIN_SOURCE - The .cpp file containing the main function
#     MAIN_FCY - The .fcy file for the module containing the main symbol
#     EXE         - The name of the final executable
#
# The section below may be modified to configure the build.

######
## Select the C++ compiler you wish to use.  Sprite was tested with g++ 4.5.2.
######
CC := g++

######
## Set the compiler flags.
######
CFLAGS := -Wall -O0 -ggdb

######
## Set the linker flags.
######
LDFLAGS := 

######
## Provide the path to Boost 1.42 or later, if necessary.
######
BOOST_HOME := $(HOME)/build/dmain/3rdparty/boost_1_42/

# ------ DON'T CHANGE ANYTHING BELOW THIS LINE ------

FLAT_CURRY := $(foreach m,$(MODULES),.sprite/$m.fcy)
MAIN_CURRY := .sprite/$(MAIN_MODULE)-main.fcy

INCLUDES := -I$(BOOST_HOME) -I$(SPRITE_HOME)/include -I.sprite
LIBS := -L$(SPRITE_HOME)/lib -lsprite
SOURCES := $(FLAT_CURRY:.fcy=.cpp)
OBJECTS := $(FLAT_CURRY:.fcy=.o)

# Builds the executable
$(EXE) : $(OBJECTS) $(MAIN_CURRY:.fcy=.o)
	$(CC) $(LDFLAGS) $^ -o $@ $(LIBS)

# Translates FlatCurry to C++
$(subst .fcy,.cpp,$(FLAT_CURRY)): %.cpp: %.fcy
	$(SPRITE_HOME)/tools/FlatCurryToSprite.state $< $@

# Generates the main source file.
$(MAIN_CURRY:.fcy=.cpp) :
	$(SPRITE_HOME)/tools/FlatCurryToSpriteMain.state $(MAIN_MODULE) $@

# Compiles C++.
.cpp.o:
	$(CC) $(CFLAGS) -c $< -o $@ $(INCLUDES)

# Additional dependencies for the main file.
$(MAIN_CURRY:.fcy=.o) : $(MAIN_FCY) $(SOURCES)

