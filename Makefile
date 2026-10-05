SUBMODULES := src curry
# The Curry library is compiled into the installation with the tools that src
# installs, so src goes first even under make -j.
curry: | src

ifeq ("$(wildcard Make.config)","")
  $(error "Make.config not found.  Please run ./configure")
endif

DIRS_TO_CLEAN += $(OBJECT_ROOT)
include Make.include

# Parallel build
# ==============
# JOBS (Make.config, configure --jobs) is the job count of the top-level
# make: a count, or auto for one job per processor.  The flag goes into
# MAKEFLAGS here, at level 0 only: the sub-makes join the job server of this
# make through the MAKEFLAGS they inherit.  A -j on the command line wins,
# and so does make JOBS=N.  The recipes below that run make say $(MAKE), so
# the job server reaches them; a plain make in a recipe runs serially, with
# a warning.  The order of the sub-makes under -j: src before curry (above),
# and inside src, cyrt before python (src/Makefile).
ifeq ($(MAKELEVEL),0)
  ifeq ($(filter -j% --jobs%,$(MAKEFLAGS)),)
    ifeq ($(strip $(JOBS)),auto)
      MAKE_JOBS := $(shell nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)
    else
      MAKE_JOBS := $(strip $(JOBS))
    endif
    ifneq ($(MAKE_JOBS),)
      ifneq ($(shell [ "$(MAKE_JOBS)" -gt 0 ] 2>/dev/null && echo ok),ok)
        $(error JOBS should be a count or auto, not "$(JOBS)".  See Make.config)
      endif
      ifneq ($(MAKE_JOBS),1)
        MAKEFLAGS += -j$(MAKE_JOBS)
      endif
    endif
  endif
endif

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
	@echo "  * Making *OPTIMIZED* flavor (no assertions).  Say \`make <target> DEBUG=1\` for debug."
endif
ifeq ($(TRACE),1)
	@echo "  * Computation tracing for 'cxx' is enabled."
else
	@echo "  * Computation tracing for 'cxx' is disabled.  Say \`make <target> TRACE=1\` to enable."
endif
ifeq ($(COUNTERS),1)
	@echo "  * The scheduler counters of 'cxx' are enabled."
else
	@echo "  * The scheduler counters of 'cxx' are disabled.  Say \`make <target> COUNTERS=1\` to enable."
endif
	@echo "  * Jobs: JOBS=$(or $(strip $(JOBS)),1) (configure --jobs N|auto).  A \`make -jN\` or \`make JOBS=N\` wins."
ifneq ($(strip $(CCACHE)),)
	@echo "  * ccache: $(CCACHE) runs in front of the compilers (configure --with-ccache)."
else
	@echo "  * ccache is not configured.  Say \`configure --with-ccache\` to put it in front of the compilers."
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
.PHONY: overlay overlay-archive overlay-interfaces $(OVERLAY_ARCHIVE) \
        $(OVERLAY_LIST_FILE)
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
# oracle tests, which extract the archive into a scratch directory.  The
# extraction is followed by overlay-interfaces: the step that writes an .icy
# file writes M.fint and M.icurry beside it, and an .icy file without them
# is stale and would be made again at its first import (see
# icurry_is_stale in curry.toolchain._curry2icurry).
overlay:
	tar xvzf $(OVERLAY_ARCHIVE) --wildcards 'tests/*'
	$(MAKE) overlay-interfaces OVERLAY_DIR=tests
endif

# Copies the interfaces of the front end beside every .icy file under
# OVERLAY_DIR: .curry/$(FRONTEND_SUBDIR)/M.fint and M.icurry of a directory
# go to .curry/$(INTERMEDIATE_SUBDIR)/ of the same directory.  The products
# of the test programs use that flat layout; the products of one archive are
# one consistent set, so the copies are sound.  A rebuilt archive packs the
# copies too, and the rule then rewrites them with the same bytes.
OVERLAY_DIR ?= tests
overlay-interfaces:
	@find $(OVERLAY_DIR) -type f -path '*/.curry/$(INTERMEDIATE_SUBDIR)/*.icy' | \
	while read -r icy; do \
	  fe="$$(dirname "$$(dirname "$$icy")")/$(FRONTEND_SUBDIR)/$$(basename "$$icy" .icy)"; \
	  for suffix in fint icurry; do \
	    if [ -f "$$fe.$$suffix" ]; then \
	      cp -p "$$fe.$$suffix" "$${icy%.icy}.$$suffix" || exit 1; \
	    fi; \
	  done; \
	done

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
	$(MAKE) -C tests

.PHONY: stage
stage:
	$(MAKE) install SYMLINK_INTERFACES=1

.PHONY: unstage
unstage:
	$(call remove_dir,$(STAGE_DIR))

# One goal per make: the Sphinx targets share the doctrees directory and
# must not run at the same time under -j.
.PHONY: docs
docs:
	$(MAKE) -C docs html
	$(MAKE) -C docs latexpdf

.PHONY: default-goal
default-goal:
	git submodule init
	git submodule update
	$(MAKE) overlay
	$(MAKE) stage

