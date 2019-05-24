SUBMODULES := src
DIRS_TO_CLEAN += $(OBJECT_ROOT)
include Make.include

# libs: $(ROOT_DIR)/sprite.a($(OBJECT_ROOT)/memory.o)

$(OBJECT_ROOT)/CMC:
	ln -s $(CMC_HOME) $@

ifdef PYTHON_EXECUTABLE
$(PREFIX)/bin:
	mkdir -p $(PREFIX)/bin
$(PREFIX)/.bin:
	mkdir -p $(PREFIX)/.bin
$(PREFIX)/.bin/python : | $(PREFIX)/.bin
	ln -s $(PYTHON_EXECUTABLE) $@
$(PREFIX)/bin/.invoker : $(ROOT_DIR)/scripts/invoker | $(PREFIX)/bin
	cp $< $@
$(PREFIX)/bin/python : | $(PREFIX)/bin
	ln -s $(PREFIX)/bin/.invoker $@
$(PREFIX)/bin/coverage : | $(PREFIX)/bin
	ln -s $(PREFIX)/bin/.invoker $@
$(PREFIX)/.bin/coverage : | $(PREFIX)/.bin
	ln -s $(PYTHON_COVERAGE_EXECUTABLE) $@
$(PREFIX)/bin/curry2json : | $(PREFIX)/bin
	ln -s $(CURRY2JSON) $@
$(PREFIX)/bin/icy : $(ROOT_DIR)/scripts/icy | $(PREFIX)/bin
	cp $< $@

$(PREFIX)/lib:
	mkdir -p $(PREFIX)/lib
$(PREFIX)/lib/curry : | $(PREFIX)/lib
	mkdir -p $(PREFIX)/lib/curry
$(PREFIX)/lib/curry/.curry : | $(PREFIX)/lib/curry
	mkdir -p $(PREFIX)/lib/curry/.curry
$(PREFIX)/lib/curry/Prelude.curry : $(CMC_HOME)/runtime/lib/Prelude.curry | $(PREFIX)/lib/curry
	cp $< $@
$(PREFIX)/lib/curry/.curry/Prelude.%    : $(CMC_HOME)/runtime/lib/.curry/Prelude.% \
                                          $(PREFIX)/lib/curry/Prelude.curry        \
                                        | $(PREFIX)/lib/curry/.curry
	cp $< $@

$(ROOT_DIR)/install:
	ln -s $(PREFIX) $@

install: $(PREFIX)/.bin/coverage                   \
         $(PREFIX)/bin/coverage                    \
         $(PREFIX)/bin/curry2json                  \
         $(PREFIX)/bin/.invoker                    \
         $(PREFIX)/.bin/python                     \
	       $(PREFIX)/bin/python                      \
	       $(PREFIX)/bin/icy                         \
         $(PREFIX)/lib/curry/Prelude.curry         \
         $(PREFIX)/lib/curry/.curry/Prelude.fcy    \
         $(PREFIX)/lib/curry/.curry/Prelude.fint   \
         $(PREFIX)/lib/curry/.curry/Prelude.icur   \
         $(PREFIX)/lib/curry/.curry/Prelude.icurry \
         $(PREFIX)/lib/curry/.curry/Prelude.json   \
         $(PREFIX)/lib/curry/.curry/Prelude.read   \
  ####
ifneq ($(PREFIX),python)
install: $(ROOT_DIR)/install
endif

uninstall:
	-rm $(PREFIX)/.bin/coverage
	-rm $(PREFIX)/bin/coverage
	-rm $(PREFIX)/bin/curry2json
	-rm $(PREFIX)/bin/.invoker
	-rm $(PREFIX)/.bin/python
	-rm $(PREFIX)/bin/python
	-rm $(PREFIX)/bin/icy
	-rm $(PREFIX)/lib/curry/Prelude.curry
	-rm -rf $(PREFIX)/lib/curry/.curry/*
	-rmdir $(PREFIX)/bin
	-rmdir $(PREFIX)/.bin
	-rmdir $(PREFIX)/lib/curry/.curry
	-rmdir $(PREFIX)/lib/curry
	-rmdir $(PREFIX)/lib
	-rmdir $(ROOT_DIR)/install
endif
