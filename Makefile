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

