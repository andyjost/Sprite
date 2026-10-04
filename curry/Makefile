# The library sources live under lib/; see Make.include.  No recursion, and
# module_names.py stays out of the installation tree.
SUBMODULES :=
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
# which would select another build flavor, another header directory, or
# another route from Curry to ICurry.  The -z option makes the plan look for
# the installed .json.z files.  The recipe fails when the products are
# missing under PREFIX afterwards.
#
# The step needs sprite-make and the tools of the installation, which src
# installs; the root Makefile orders curry after src.  An install of this
# directory alone (as tests/unit_currylib.py runs it) has no sprite-make and
# skips the step with a notice.  The FlatCurry interfaces of the library are
# written first, so the front end reads them instead of writing them again.
#
# Every module under lib/ (CURRYLIB_MODULES) gets its ICurry and JSON
# (sprite-make --json), so no run of Sprite writes into the installation for
# a library module.  The modules Sprite can compile (CURRYLIB_PREBUILD_MODULES;
# see CURRYLIB_UNSUPPORTED_MODULES in the root Make.include) get the generated
# Python and, with a compiler, the shared objects.
PREBUILD_ENV := env -u CURRYPATH -u CFLAGS -u CXXFLAGS \
                    -u SPRITE_INTERPRETER_FLAGS -u SPRITE_CXX_PCH_ROOT \
                    -u SPRITE_FORCE_RECOMPILE_CXX -u SPRITE_CURRY2ICURRY \
                    SPRITE_HOME=$(PREFIX)
PREBUILD_CHECK = test -f $(CURRYLIB_INSTALL_SUBDIR)/Prelude$(1) \
                 || { echo "prebuild: $(CURRYLIB_INSTALL_SUBDIR)/Prelude$(1)" \
                           "was not written" >&2; exit 1; }
.PHONY: prebuild
prebuild: $(CURRYLIB_INSTALL_FILES) $(CURRYLIB_FLAT_STAMP)
	@if [ ! -x $(PREFIX)/bin/sprite-make ]; then \
	  echo "Skipping the prebuild of the Curry library:" \
	       "no sprite-make under $(PREFIX)/bin (install src first)."; \
	  exit 0; \
	fi; \
	echo $(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --json -zc $(CURRYLIB_MODULES); \
	$(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --json -zc $(CURRYLIB_MODULES) \
	  || exit 1; \
	echo $(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --py -zc $(CURRYLIB_PREBUILD_MODULES); \
	$(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --py -zc $(CURRYLIB_PREBUILD_MODULES) \
	  || exit 1; \
	$(call PREBUILD_CHECK,.py); \
	if [ -x $(PREFIX)/tools/cxx ]; then \
	  echo $(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --so -zc $(CURRYLIB_PREBUILD_MODULES); \
	  $(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --so -zc $(CURRYLIB_PREBUILD_MODULES) \
	    || exit 1; \
	  $(call PREBUILD_CHECK,.so); \
	  $(call PREBUILD_CHECK,.so.abi); \
	else \
	  echo "Skipping the C++ build of the Curry library:" \
	       "no C++ compiler at $(PREFIX)/tools/cxx."; \
	fi
install:: prebuild
