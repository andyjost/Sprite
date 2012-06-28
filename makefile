include config/makesetup

vpath %.cpp src
vpath %.hpp include
vpath %.curry tools currylib
OBJDIR=obj
CURRYLIBDIR=currylib/.sprite

INCLUDES := -I$(BOOST_HOME) -Iinclude
OBJECTS := $(addprefix $(OBJDIR)/, cmdline.o exec.o system.o)
LIB := lib/libsprite.a

STATES = $(addprefix tools/, FlatCurryToSpriteMain.state FlatCurryToSprite.state)

# The headers files in currylib.
CURRYLIBHEADERS := $(addprefix $(CURRYLIBDIR)/, SpritePrelude.hpp)

install: $(LIB) states currylib

# Builds the state files.  Add the lib directory Curry files as a dependency to
# trigger a rebuild when they change.
states: $(STATES)
tools/%.state: %.curry $(wildcard lib/*.curry)
	cd tools && ./compileState $(basename $(notdir $@))

# Builds libsprite.a.
$(LIB): $(OBJECTS)
	rm -f $@
	ar -r $@ $^

# The currylib dependency is because SpritePrelude.hpp is requied by some .cpp
# files.  
$(OBJDIR)/%.o: %.cpp currylib
	@mkdir -p $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@ $(INCLUDES)

# Builds the files under currylib.
currylib: $(CURRYLIBHEADERS)
$(CURRYLIBDIR)/%.hpp: $(STATES)
	cd currylib && ../bin/sprite -c $(basename $(notdir $@))

.PHONY: clean
clean:
	rm -rf $(OBJDIR) tools/*.state lib/libsprite.a currylib/.sprite

# This target is intended to leave things that require pakcs so that a build
# can be moved to a machine that has no packs installed.
.PHONY: cleancpp
cleancpp:
	rm -rf $(OBJDIR) lib/libsprite.a
