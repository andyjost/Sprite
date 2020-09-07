SUBMODULES := src
DIRS_TO_CLEAN += $(OBJECT_ROOT)
include Make.include

.DEFAULT_GOAL := $(ROOT_DIR)/install

# libs: $(ROOT_DIR)/sprite.a($(OBJECT_ROOT)/memory.o)

$(OBJECT_ROOT)/CMC:
	ln -s $(CMC_HOME) $@

.PHONY: MANIFEST
MANIFEST:
	cd $(PREFIX) && tree -anps -o $(ROOT_DIR)/MANIFEST

ifdef PYTHON_EXECUTABLE
$(PREFIX)/bin:
	mkdir -p $(PREFIX)/bin
$(PREFIX)/.bin:
	mkdir -p $(PREFIX)/.bin
$(PREFIX)/.bin/python : | $(PREFIX)/.bin
	ln -s $(PYTHON_EXECUTABLE) $@
$(PREFIX)/bin/python : | $(PREFIX)/bin
	ln -s .invoker $@
$(PREFIX)/bin/coverage : | $(PREFIX)/bin
	ln -s .invoker $@
$(PREFIX)/.bin/coverage : | $(PREFIX)/.bin
	ln -s $(PYTHON_COVERAGE_EXECUTABLE) $@
$(PREFIX)/.bin/curry2json : | $(PREFIX)/bin
	ln -s $(CURRY2JSON) $@
$(PREFIX)/bin/.invoker : $(ROOT_DIR)/src/export/invoker.script | $(PREFIX)/bin
	cp $< $@
	chmod 554 $@
$(PREFIX)/bin/icy : $(ROOT_DIR)/src/export/icy.script | $(PREFIX)/bin
	cp $< $@
	chmod 554 $@
$(PREFIX)/bin/curryexec : $(ROOT_DIR)/src/export/curryexec.script | $(PREFIX)/bin
	cp $< $@
	chmod 554 $@
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
         $(PREFIX)/.bin/curry2json                 \
         $(PREFIX)/bin/.invoker                    \
         $(PREFIX)/.bin/python                     \
         $(PREFIX)/bin/python                      \
         $(PREFIX)/bin/icy                         \
         $(PREFIX)/bin/curryexec                   \
         $(PREFIX)/lib/curry/Prelude.curry         \
         $(PREFIX)/lib/curry/.curry/Prelude.fcy    \
         $(PREFIX)/lib/curry/.curry/Prelude.fint   \
         $(PREFIX)/lib/curry/.curry/Prelude.icur   \
         $(PREFIX)/lib/curry/.curry/Prelude.icurry \
         $(PREFIX)/lib/curry/.curry/Prelude.json   \
         $(PREFIX)/lib/curry/.curry/Prelude.read   \
  ####
	@echo "\n****** Sprite is installed under $(PREFIX) ******\n"

ifneq ($(PREFIX),python)
install: $(ROOT_DIR)/install
endif

uninstall:
	-rm -f $(PREFIX)/.bin/coverage
	-rm -f $(PREFIX)/bin/coverage
	-rm -f $(PREFIX)/.bin/curry2json
	-rm -f $(PREFIX)/bin/.invoker
	-rm -f $(PREFIX)/.bin/python
	-rm -f $(PREFIX)/bin/python
	-rm -f $(PREFIX)/bin/icy
	-rm -f $(PREFIX)/bin/curryexec
	-rm -f $(PREFIX)/lib/curry/Prelude.curry
	-rm -rf $(PREFIX)/lib/curry/.curry/*
	-rmdir $(PREFIX)/bin
	-rmdir $(PREFIX)/.bin
	-rmdir $(PREFIX)/lib/curry/.curry
	-rmdir $(PREFIX)/lib/curry
	-rmdir $(PREFIX)/lib
	-rmdir $(ROOT_DIR)/install
endif
