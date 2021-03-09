SUBMODULES := src curry

DIRS_TO_CLEAN += $(OBJECT_ROOT)
include Make.include

.DEFAULT_GOAL := help

.PHONY: MANIFEST
MANIFEST:
	cd $(PREFIX) && tree -anps -o $(ROOT_DIR)/MANIFEST

# Usage
# =====
.PHONY: help
help:
	@echo "              WELCOME TO THE SPRITE BUILD SYSTEM!"
	@echo "              ==================================="
	@echo ""
	@echo "Usage: make [target ...] [var=value ...]"
	@echo ""
	@echo "Targets for building Sprite:"
	@echo "    all    : build objects, libraries, and executables"
	@echo "    clean  : remove generated files"
	@echo "    objs   : compile object files"
	@echo "    libs   : compile and link static libraries"
	@echo "    shlibs : compile and link shared libraries"
	@echo ""
	@echo "Targets for installing Sprite:"
	@echo "    install PREFIX=<dirname>   : install files under <dirname>"
	@echo "    uninstall PREFIX=<dirname> : uninstall files under <dirname>"
	@echo ""
	@echo "PREFIX is set to $(PREFIX)"
	@echo ""
	@echo "Targets for debugging the build system:"
	@echo "    print-<varname> : print the value of make variable <varname>"
	@echo ""
	@echo "Example:"
	@echo "    make all               --build everything"
	@echo "    make install ~/sprite  --install Sprite to "'$$HOME'"/sprite"
	@echo ""
	@echo "For information on testing, refer to tests/README."
	@echo ""
# @echo "To build documentation, add WITHDOC=1 to the commandline or invoke"
# @echo "make from the docs/ subdirectory."

ifdef PYTHON_EXECUTABLE
# $(PREFIX)/bin:
# 	mkdir -p $(PREFIX)/bin
# $(PREFIX)/.bin:
# 	mkdir -p $(PREFIX)/.bin
# $(PREFIX)/.bin/python : | $(PREFIX)/.bin
# 	ln -s $(PYTHON_EXECUTABLE) $@
# $(PREFIX)/.bin/icurry : | $(PREFIX)/.bin
# 	ln -s $(ICURRY_EXECUTABLE) $@
# $(PREFIX)/.bin/icurry2json : | $(PREFIX)/.bin
# 	ln -s $(ICURRY2JSON_EXECUTABLE) $@
# $(PREFIX)/bin/python : | $(PREFIX)/bin
# 	ln -s .invoker $@
# $(PREFIX)/bin/coverage : | $(PREFIX)/bin
# 	ln -s .invoker $@
# $(PREFIX)/.bin/coverage : | $(PREFIX)/.bin
# 	@if [ ! -f $(PYTHON_COVERAGE_EXECUTABLE) ] || [ ! -x $(PYTHON_COVERAGE_EXECUTABLE) ]; then \
# 	  echo 1>&2 "*** Not an executable file: PYTHON_COVERAGE_EXECUTABLE=$(PYTHON_COVERAGE_EXECUTABLE)"; \
# 	  echo 1>&2 "    Perhaps you need to install it:"; \
# 	  echo 1>&2 "        $(PYTHON_HOME)/bin/pip install coverage"; \
# 	  echo 1>&2 "*** $@ is an invalid link"; \
# 	else \
# 	  ln -s $(PYTHON_COVERAGE_EXECUTABLE) $@; \
#   fi
# $(PREFIX)/.bin/icurry : | $(PREFIX)/.bin
# 	ln -s $(ICURRY) $@
# $(PREFIX)/.bin/icurry2json : | $(PREFIX)/.bin
# 	ln -s $(ICURRY2JSON) $@

# $(PREFIX)/bin/% : $(ROOT_DIR)/src/export/%.script | $(PREFIX)/bin
# 	cp $< $@
# 	chmod 554 $@
# $(PREFIX)/bin/.invoker : $(ROOT_DIR)/src/export/invoker.script | $(PREFIX)/bin
# 	cp $< $@
# 	chmod 554 $@
# $(PREFIX)/bin/icy : $(ROOT_DIR)/src/export/icy.script | $(PREFIX)/bin
# 	cp $< $@
# 	chmod 554 $@
# $(PREFIX)/bin/curryexec : $(ROOT_DIR)/src/export/curryexec.script | $(PREFIX)/bin
# 	cp $< $@
# 	chmod 554 $@

$(ROOT_DIR)/install:
	ln -s $(PREFIX) $@

# install: $(PREFIX)/.bin/coverage                   \
#          $(PREFIX)/bin/coverage                    \
#          $(PREFIX)/.bin/curry2json                 \
#          $(PREFIX)/bin/.invoker                    \
#          $(PREFIX)/.bin/python                     \
#          $(PREFIX)/bin/python                      \
#          $(PREFIX)/bin/icy                         \
#          $(PREFIX)/bin/curryexec                   \
#          $(PREFIX)/bin/cy2json                     \
#   ####
# 	@echo "\n****** Sprite is installed under $(PREFIX) ******\n"

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
	-if [ -d $(PREFIX)/bin ];              then rmdir $(PREFIX)/bin;              fi
	-if [ -d $(PREFIX)/.bin ];             then rmdir $(PREFIX)/.bin;             fi
	-if [ -d $(PREFIX)/lib ];              then rmdir $(PREFIX)/lib;              fi
ifeq ($(PREFIX),$(ROOT_DIR)/install)
	-rmdir $(ROOT_DIR)/install
endif
endif
