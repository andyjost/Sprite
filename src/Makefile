CFLAGS=-O3 -Wall
CPPFLAGS=$(CFLAGS) -std=c++11

DEPDIR := .d
$(shell mkdir -p $(DEPDIR) >/dev/null)
DEPFLAGS = -MT $@ -MMD -MP -MF $(DEPDIR)/$*.Td
POSTCOMPILE = @mv -f $(DEPDIR)/$*.Td $(DEPDIR)/$*.d && touch $@

cymps.o: cymps.c $(DEPDIR)/cymps.d
	gcc -c cymps.c $(CFLAGS) $(DEPFLAGS) -DCONFIG_VAR_HOT -Imps -Wno-maybe-uninitialized
	$(POSTCOMPILE)

main.o: main.cpp
	g++ -c main.cpp $(CFLAGS) -Wno-switch
	g++ main.o mps/mps.o -lpthread -o go

all:
	./build

include $(wildcard $(patsubst %,$(DEPDIR)/%.d,$(basename $(SRCS))))
