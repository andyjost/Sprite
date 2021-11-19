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
	@echo "Usage: make [target ...] [var=value ...]"
	@echo ""
	@echo "************************************************"
	@echo "    To build and install, say \`make install\`"
	@echo "************************************************"
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
$(OVERLAY_FILE):
	find curry src tests -type f -wholename '*/.curry/*$(PAKCS_SUBDIR)*' | xargs tar cvzf $@
.PHONY: overlay overlay-install
overlay: $(OVERLAY_FILE)
install-overlay:
	tar xvzf $(OVERLAY_FILE)
