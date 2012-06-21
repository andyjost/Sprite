include config/makesetup

vpath %.cpp src
vpath %.hpp include
#vpath %.o obj
OBJDIR=obj
CURRYLIBDIR=currylib/.sprite

INCLUDES := -I$(BOOST_HOME) -Iinclude
OBJECTS := $(addprefix $(OBJDIR)/, builtins.o exec.o system.o)
LIB := lib/libsprite.a

STATES = $(addprefix tools/, FlatCurryToSpriteMain.state FlatCurryToSprite.state)

# The headers files in currylib.
CURRYLIBHEADERS := $(addprefix $(CURRYLIBDIR)/, SpritePrelude.hpp)

install: $(LIB) $(STATES) currylib

# Builds the state files.
tools/%.state : 
	cd tools && ./compileState $(basename $(notdir $@))

# Builds libsprite.a.
$(LIB) : $(OBJECTS)
	rm -f $@
	ar -r $@ $^

currylib : $(CURRYLIBHEADERS)

# Builds the Curry library files.
$(OBJDIR)/%.o: %.cpp
	mkdir -p $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@ $(INCLUDES)

# Builds the files under currylib.
$(CURRYLIBDIR)/%.hpp:
	cd currylib && sprite -c $(basename $(notdir $@))

.PHONY: clean
clean:
	rm -rf $(OBJDIR) tools/*.state lib/libsprite.a
