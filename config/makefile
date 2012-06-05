# Use this makefile to configure how Sprite builds Curry programs.  This file
# will be included after the following variables are defined:
#
#     MODULES     - The list of Curry modules required for the program
#     MAIN_MODULE - The Curry module containing the main function
#     EXE         - The name of the final executable
#
# The section below may be modified to configure the build.

include $(SPRITE_HOME)/config/makesetup

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

