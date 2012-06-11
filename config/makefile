# Use this makefile to configure how Sprite builds Curry programs.  This file
# will be included after the following variables are defined:
#
#     MODULES     - The list of Curry modules required for the program
#     MAIN_MODULE - The Curry module containing the main function
#     EXE         - The name of the final executable
#

include $(SPRITE_HOME)/config/makesetup

vpath %.fcy ../.curry

FLAT_CURRY := $(foreach m,$(MODULES),$m.fcy)
MAIN_SOURCE := $(MAIN_MODULE)-main.cpp

INCLUDES := -I$(BOOST_HOME) -I$(SPRITE_HOME)/include -I.
LIBS := -L$(SPRITE_HOME)/lib -lsprite
SOURCES := $(FLAT_CURRY:.fcy=.cpp)
OBJECTS := $(FLAT_CURRY:.fcy=.o)

# Builds the executable
$(EXE) : $(OBJECTS) $(MAIN_SOURCE:.cpp=.o)
	$(CC) $(LDFLAGS) $^ -o $@ $(LIBS)

# Translates FlatCurry to C++
%.cpp: %.fcy
	$(SPRITE_HOME)/tools/FlatCurryToSprite.state $< $@
	# pakcs -q -r $(SPRITE_HOME)/tools/FlatCurryToSprite.curry $< $@

# Generates the main source file.
$(MAIN_SOURCE) :
	$(SPRITE_HOME)/tools/FlatCurryToSpriteMain.state $(MAIN_MODULE) $@
	# pakcs -q -r $(SPRITE_HOME)/tools/FlatCurryToSpriteMain.curry $(MAIN_MODULE) $@

# Compiles C++.
.cpp.o:
	$(CC) $(CFLAGS) -c $< -o $@ $(INCLUDES)

# Additional dependencies for the main file.
$(MAIN_SOURCE:.cpp=.o) : $(SOURCES)
