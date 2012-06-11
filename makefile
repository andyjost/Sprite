include config/makesetup

vpath %.cpp src
vpath %.hpp include
vpath %.o obj
OBJDIR=obj

INCLUDES := -I$(BOOST_HOME) -Iinclude
OBJECTS := $(addprefix $(OBJDIR)/, builtins.o exec.o system.o)
LIB := lib/libsprite.a

install: $(LIB) states

.PHONY: states
states : 
	./compileStates

$(LIB) : $(OBJECTS)
	rm -f $@
	ar -r $@ $^

$(OBJDIR)/%.o: %.cpp $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@ $(INCLUDES)

$(OBJDIR):
	mkdir -p $(OBJDIR)

.PHONY: clean
clean:
	rm -rf $(OBJDIR)
