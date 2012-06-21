include config/makesetup

vpath %.cpp src
vpath %.hpp include
vpath %.curry tools currylib
OBJDIR=obj
CURRYLIBDIR=currylib/.sprite

INCLUDES := -I$(BOOST_HOME) -Iinclude
OBJECTS := $(addprefix $(OBJDIR)/, builtins.o exec.o system.o)
LIB := lib/libsprite.a

STATES = $(addprefix tools/, FlatCurryToSpriteMain.state FlatCurryToSprite.state)

# The headers files in currylib.
CURRYLIBHEADERS := $(addprefix $(CURRYLIBDIR)/, SpritePrelude.hpp)

install: $(LIB) states currylib

# Builds the state files.
states: $(STATES)
tools/%.state: %.curry
	cd tools && ./compileState $(basename $(notdir $@))

# Builds libsprite.a.
$(LIB): $(OBJECTS)
	rm -f $@
	ar -r $@ $^

# Builds the Curry library files.
currylib: $(CURRYLIBHEADERS)
$(OBJDIR)/%.o: %.cpp
	mkdir -p $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@ $(INCLUDES)

# Builds the files under currylib.
$(CURRYLIBDIR)/%.hpp:
	cd currylib && sprite -c $(basename $(notdir $@))

.PHONY: clean
clean:
	rm -rf $(OBJDIR) tools/*.state lib/libsprite.a
