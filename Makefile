SUBMODULES := src curry

DIRS_TO_CLEAN += $(OBJECT_ROOT)
include Make.include

.DEFAULT_GOAL := default-goal

.PHONY: MANIFEST
MANIFEST:
	cd $(PREFIX) && tree -anps -o $(ROOT_DIR)/MANIFEST

# Usage
# =====
.PHONY: help
help:
	@echo "Usage: make [target ...] [var=value ...]"
	@echo ""
	@echo "******************************************************"
	@echo "    To build, stage, and test, say \`make install\`"
	@echo "******************************************************"
	@echo ""
	@echo "  * Installing to PREFIX=$(PREFIX)."
ifeq ($(DEBUG),1)
	@echo "  * Making *DEBUG* flavor."
else
	@echo "  * Making *OPTIMIZED* flavor.  Say \`make <target> DEBUG=1\` for debug."
endif
	@echo ""
	@echo "Targets for building:"
	@echo "---------------------"
	@echo "    all    : build objects and libraries"
	@echo "    clean  : remove generated files"
	@echo "    objs   : compile object files"
	@echo "    libs   : compile and link static libraries"
	@echo "    shlibs : compile and link shared libraries"
	@echo ""
	@echo "Targets for installing:"
	@echo "-----------------------"
	@echo "    install PREFIX=<dirname>   : install files under <dirname>"
	@echo "    uninstall PREFIX=<dirname> : uninstall files under <dirname>"
	@echo ""
	@echo "Targets to overlay PAKCS files (improves test speed):"
	@echo "-----------------------------------------------------"
	@echo "    overlay      : overlay PAKCS files"
	@echo "    overlay-file : build a new tarball of overlayable files"
	@echo ""
	@echo "Targets for debugging:"
	@echo "----------------------"
	@echo "    print-<varname> : print the value of a make variable;  E.g., say"
	@echo "                      \`make print-CC\` to see the selected compiler."
	@echo ""
	@echo "For information on testing, refer to tests/README."
	@echo ""
# @echo "To build documentation, add WITHDOC=1 to the commandline or invoke"
# @echo "make from the docs/ subdirectory."

# The overlay file captures build products for a particular version of PAKCS.
# Installing these dramatically improves the test performance.
OVERLAY_FILE := overlay-$(PAKCS_SUBDIR).tgz
.PHONY: overlay overlay-file $(OVERLAY_FILE)
$(OVERLAY_FILE):
	find curry src tests -type f -wholename '*/.curry/*$(PAKCS_SUBDIR)*' | xargs tar cvzf $@
overlay-file: $(OVERLAY_FILE)
ifeq ($(shell [ -e $(OVERLAY_FILE) ]; echo $$?),1)
overlay:
else
overlay:
	tar xvzf $(OVERLAY_FILE)
endif

.PHONY: test
test:
	make -C tests

.PHONY: stage
stage:
	make install

.PHONY: docs
docs:
	make -C docs html latexpdf

.PHONY: default-goal
default-goal:
	git submodule init
	git submodule update
	make stage
	make overlay
	make test

