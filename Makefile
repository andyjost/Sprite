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

# Usage
# =====
.PHONY: help
help:
	@echo "Usage: make [target ...] [var=value ...]"
	@echo "Build targets:"
	@echo "    all     : build objects, libraries, and executables"
	@echo "    clean   : remove generated files"
	@echo "    objs    : compile object files"
	@echo "    libs    : compile and link static libraries"
	@echo "    shlibs  : compile and link shared libraries"
	@echo ""
	@echo "Install targets:"
	@echo "    install PREFIX=<dirname>   : install files under <dirname>"
	@echo "    uninstall PREFIX=<dirname> : uninstall files under <dirname>"
	@echo ""
	@echo "Debug targets:"
	@echo "    print-<varname>: print the value of make variable <varname>"
	@echo ""
	@echo "Example:"
	@echo "    make all"
	@echo "    make install ~/sprite  --install under home directory"
	@echo ""
	@echo "For testing information, please see tests/README."
	@echo ""
	# @echo "To build documentation, add WITHDOC=1 to the commandline or invoke"
	# @echo "make from the docs/ subdirectory."

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
	@if [ ! -f $(PYTHON_COVERAGE_EXECUTABLE) ] || [ ! -x $(PYTHON_COVERAGE_EXECUTABLE) ]; then \
	  echo 1>&2 "*** Not an executable file: PYTHON_COVERAGE_EXECUTABLE=$(PYTHON_COVERAGE_EXECUTABLE)"; \
	  echo 1>&2 "    Perhaps you need to install it:"; \
	  echo 1>&2 "        $(PYTHON_HOME)/bin/pip install coverage"; \
	  echo 1>&2 "*** $@ is an invalid link"; \
	else \
	  ln -s $(PYTHON_COVERAGE_EXECUTABLE) $@; \
  fi
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
