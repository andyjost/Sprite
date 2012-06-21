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
HEADERS := $(FLAT_CURRY:.fcy=.hpp)

# Builds the executable
$(EXE) : $(MAIN_SOURCE:.cpp=.o)
	$(CC) $(LDFLAGS) $^ -o $@ $(LIBS)

# Build the module headers only.
modules : $(HEADERS)

# Translates FlatCurry to C++
# pakcs -q -r $(SPRITE_HOME)/tools/FlatCurryToSprite.curry $< $@
%.hpp: %.fcy
	$(SPRITE_HOME)/tools/FlatCurryToSprite.state $< $@

# Generates the main source file.
# pakcs -q -r $(SPRITE_HOME)/tools/FlatCurryToSpriteMain.curry $(MAIN_MODULE) $@
$(MAIN_SOURCE) :
	$(SPRITE_HOME)/tools/FlatCurryToSpriteMain.state $(MAIN_MODULE) $@

# Compiles C++.
.cpp.o:
	$(CC) $(CFLAGS) -c $< -o $@ $(INCLUDES)

# Additional dependencies for the main file.
$(MAIN_SOURCE:.cpp=.o) : $(HEADERS)
