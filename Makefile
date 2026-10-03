SUBMODULES := src curry
# The Curry library is compiled into the installation with the tools that src
# installs, so src goes first even under make -j.
curry: | src

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
	@echo "  * See Make.config for editable configuration options."
	@echo "  * Installing to PREFIX=$(PREFIX)."
ifeq ($(DEBUG),1)
	@echo "  * Making *DEBUG* flavor."
else
	@echo "  * Making *OPTIMIZED* flavor.  Say \`make <target> DEBUG=1\` for debug."
endif
ifeq ($(TRACE),1)
	@echo "  * Computation tracing for 'cxx' is enabled."
else
	@echo "  * Computation tracing for 'cxx' is disabled.  Say \`make <target> TRACE=1\` to enable."
endif
	@echo ""
	@echo "Targets for testing:"
	@echo "--------------------"
	@echo "    stage  : build a local copy for testing"
	@echo "    test   : run unit tests (must stage first)"
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
	@echo "Targets to overlay prebuilt test products (improves test speed):"
	@echo "-----------------------------------------------------------------"
	@echo "    overlay         : extract the prebuilt products of the test programs"
	@echo "    overlay-archive : build a new archive of the test products"
	@echo ""
	@echo "Targets for debugging the build:"
	@echo "--------------------------------"
	@echo "    print-<varname> : print the value of a make variable;  E.g., say"
	@echo "                      \`make print-CC\` to see the selected compiler."
	@echo ""
	@echo "For information on testing, refer to tests/README."
	@echo ""
# @echo "To build documentation, add WITHDOC=1 to the commandline or invoke"
# @echo "make from the docs/ subdirectory."

# The overlay archive holds the FlatCurry and ICurry products of the test
# programs and the FlatCurry interfaces of the Curry library, for the pinned
# PAKCS.  Extracting the test products makes the tests much faster.  The
# archive is also the fixed oracle of the FlatCurry-to-ICurry port: its .icy
# files were written by icurry 3.1.0 (see tests/README, section 8).
#
# overlay-archive packs the products on disk.  Rebuild the archive only from
# .icy files that icurry wrote (SPRITE_CURRY2ICURRY=icurry), never from the
# output of the port that the oracle checks.  Only the five product kinds are
# packed; the compiled forms beside them (.py, .cpp, .so) are left out.  The
# library interfaces come from the front end (make -C curry interfaces).  The
# metadata is fixed, so the archive names no user, and the same products give
# the same bytes.
OVERLAY_ARCHIVE := overlay-$(PAKCS_SUBDIR).tgz
OVERLAY_LIST_FILE := OVERLAY_FILES.txt
OVERLAY_PRODUCTS := -name '*.fcy' -o -name '*.fint' -o -name '*.icurry' \
                    -o -name '*.icy' -o -name '*.json.z'
OVERLAY_TAR_FLAGS := --sort=name --owner=0 --group=0 --numeric-owner \
                     --mtime='2000-01-01 00:00:00Z'
.PHONY: overlay overlay-archive $(OVERLAY_ARCHIVE) $(OVERLAY_LIST_FILE)
$(OVERLAY_LIST_FILE):
	$(MAKE) -C curry interfaces
	find tests curry/lib -type f -path '*/.curry/*$(PAKCS_SUBDIR)/*' \
	    \( $(OVERLAY_PRODUCTS) \) | LC_ALL=C sort > $@
$(OVERLAY_ARCHIVE): $(OVERLAY_LIST_FILE)
	tar c $(OVERLAY_TAR_FLAGS) -T $(OVERLAY_LIST_FILE) | gzip -n > $@
	rm $(OVERLAY_LIST_FILE)
overlay-archive: $(OVERLAY_ARCHIVE)
ifeq ($(shell [ -e $(OVERLAY_ARCHIVE) ]; echo $$?),1)
overlay:
else
# Only the test products are extracted.  The library interfaces serve the
# oracle tests, which extract the archive into a scratch directory.
overlay:
	tar xvzf $(OVERLAY_ARCHIVE) --wildcards 'tests/*'
endif

# Remove a directory.  If the path is a symlink, remove the contents of the
# link target and keep the link.
define remove_dir =
@if [ -z "$(strip $1)" ]; then echo "remove_dir: empty path" 1>&2; exit 1; \
elif [ -L "$1" ] && [ -d "$1" ]; then echo "rm -rf $$(realpath $1)/*"; \
  find "$$(realpath $1)" -mindepth 1 -maxdepth 1 -exec rm -rf {} +; \
elif [ -e "$1" ]; then echo rm -r $1; rm -r $1; fi
endef

.PHONY: clean
clean:
	$(call remove_dir,$(OBJECT_ROOT))

.PHONY: test
test:
	make -C tests

.PHONY: stage
stage:
	make install SYMLINK_INTERFACES=1

.PHONY: unstage
unstage:
	$(call remove_dir,$(STAGE_DIR))

.PHONY: docs
docs:
	make -C docs html latexpdf

.PHONY: default-goal
default-goal:
	git submodule init
	git submodule update
	make overlay
	make stage

