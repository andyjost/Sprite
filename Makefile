SUBMODULES := src curry

ifeq ("$(wildcard Make.config)","")
  $(error "Make.config not found.  Please run ./configure")
endif

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
	@echo "  * See Make.config for editable configuration options."
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
	@echo "    overlay         : overlay PAKCS files"
	@echo "    overlay-archive : build a new archive of overlayable files"
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

# The overlay archive captures build products for a particular version of
# PAKCS.  Installing these dramatically improves the test performance.
OVERLAY_ARCHIVE := overlay-$(PAKCS_SUBDIR).tgz
OVERLAY_LIST_FILE := OVERLAY_FILES.txt
.PHONY: overlay overlay-archive $(OVERLAY_ARCHIVE) $(OVERLAY_LIST_FILE)
$(OVERLAY_LIST_FILE):
	find tests -type f -wholename '*/.curry/*$(PAKCS_SUBDIR)*' >  $(OVERLAY_LIST_FILE)
	find curry/$(PAKCS_SUBDIR) -type f                         >> $(OVERLAY_LIST_FILE)
$(OVERLAY_ARCHIVE): $(OVERLAY_LIST_FILE)
	tar cvT $(OVERLAY_LIST_FILE) | gzip -n > $@
	rm $(OVERLAY_LIST_FILE)
overlay-archive: $(OVERLAY_ARCHIVE)
ifeq ($(shell [ -e $(OVERLAY_ARCHIVE) ]; echo $$?),1)
overlay:
else
overlay:
	tar xvzf $(OVERLAY_ARCHIVE)
endif

.PHONY: test
test:
	make -C tests

.PHONY: stage
stage:
	make install SYMLINK_PYTHON=1

.PHONY: docs
docs:
	make -C docs html latexpdf

.PHONY: default-goal
default-goal:
	git submodule init
	git submodule update
	make overlay
	make stage
	make test

