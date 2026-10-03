SUBMODULES := Control Data
CURRYLIB_SRC_FILES := Prelude.curry $(wildcard *.curry)
CURRYFILES :=
PYTHONFILES :=
include Make.include

# Compile the installed Curry library for both backends, so that the first
# import after a stage compiles nothing: the Python backend finds the
# generated module and its bytecode cache, and the C++ backend finds the
# shared object, its ABI stamp, and the precompiled header.  sprite-make
# skips a module whose files are current.  The C++ part is skipped when the
# installation has no C++ compiler; the C++ backend then compiles the
# library on first use.  The library is built against the installed files
# only, in the installation this make writes: sprite-invoke keeps an
# exported SPRITE_HOME, so the recipe sets it to PREFIX.  CURRYPATH must not
# reach sprite-make, and neither must the compiler flags of this build, which
# make exports when the shell set them, nor the run-time variables of Sprite,
# which would select another build flavor or another header directory.  The
# -z option makes the plan look for the installed .json.z files.  The recipe
# fails when the products are missing under PREFIX afterwards.
SYSLIB_MODULES := $(shell cd $(ROOT_DIR)/curry \
                          && $(PYTHON_EXECUTABLE) module_names.py)
PREBUILD_ENV := env -u CURRYPATH -u CFLAGS -u CXXFLAGS \
                    -u SPRITE_INTERPRETER_FLAGS -u SPRITE_CXX_PCH_ROOT \
                    -u SPRITE_FORCE_RECOMPILE_CXX SPRITE_HOME=$(PREFIX)
PREBUILD_CHECK = test -f $(CURRYLIB_INSTALL_SUBDIR)/Prelude$(1) \
                 || { echo "prebuild: $(CURRYLIB_INSTALL_SUBDIR)/Prelude$(1)" \
                           "was not written" >&2; exit 1; }
.PHONY: prebuild
prebuild: $(CURRYLIB_INSTALL_FILES) | $(SUBMODULES)
	$(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --py -zc $(SYSLIB_MODULES)
	@$(call PREBUILD_CHECK,.py)
	@if [ -x $(PREFIX)/tools/cxx ]; then \
	  echo $(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --so -zc $(SYSLIB_MODULES); \
	  $(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --so -zc $(SYSLIB_MODULES) \
	    || exit 1; \
	  $(call PREBUILD_CHECK,.so); \
	  $(call PREBUILD_CHECK,.so.abi); \
	else \
	  echo "Skipping the C++ build of the Curry library:" \
	       "no C++ compiler at $(PREFIX)/tools/cxx."; \
	fi
install:: prebuild
