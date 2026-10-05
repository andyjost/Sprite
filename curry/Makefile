# The library sources live under lib/; see Make.include.  No recursion, and
# module_names.py stays out of the installation tree.
SUBMODULES :=
PYTHONFILES :=
include Make.include

# The targets of this directory run one at a time, also under make -j.  The
# install copies are cheap, and the other steps must not overlap: the front
# end and sprite-make write products that several modules share (the
# FlatCurry interfaces, the ICurry of the imports) when icy or json rebuilds
# the pinned artifacts.
.NOTPARALLEL:

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
# written first, so the front end reads them instead of writing them again,
# and copied beside the products (see Make.include), so sprite-make finds the
# pinned modules current.
#
# The step is one recipe, and the modules are not independent targets:
# every module imports the Prelude, and many import each other; the step
# that compiles a module imports its imports, and compiles one whose files
# are stale on the spot, so two make jobs over the library would compile a
# shared import at the same time.  Instead, the C++ step runs sprite-make
# --jobs, which compiles the modules in child processes, the imports of a
# module before the module, and makes no child for a module whose files are
# current.  The ICurry and Python steps stay serial: they take a few seconds
# together, and a child process per module costs more than it saves there.
# PREBUILD_JOBS is the count of this make: the -jN that MAKEFLAGS carries
# into a sub-make (the root Makefile turns JOBS of Make.config into -j; a
# bare -j is auto), else JOBS itself, so that make -C curry install follows
# the configured width too.  JOBS=1 keeps the serial run.  The children of
# sprite-make are outside the job server of make; the prebuild runs after
# src is installed and nothing else runs beside it.  The Prelude bounds the
# step: its shared object is one translation unit, and every other module
# waits for it.  The order of sprite-make covers the files it writes, not
# the interface files of the front end (.fint, .fcy), which the front end
# writes for an import on its own when they are missing.  That hazard does
# not arise here: the ICurry of every library module is committed and the
# JSON step derives from it, so the children of the C++ step never run the
# front end.
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
# Expanded in the recipe: while the makefiles are read, MAKEFLAGS holds the
# -j without its count.
PREBUILD_JOBS = $(if $(filter -j%,$(MAKEFLAGS)),\
                  $(or $(strip $(patsubst -j%,%,$(filter -j%,$(MAKEFLAGS)))),auto),\
                  $(or $(strip $(JOBS)),1))
PREBUILD_SO_FLAGS = --jobs $(strip $(PREBUILD_JOBS)) -zc
.PHONY: prebuild
prebuild: $(CURRYLIB_INSTALL_FILES) $(CURRYLIB_FLAT_STAMP) $(CURRYLIB_INSTALL_IFACE)
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
	  echo $(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --so $(PREBUILD_SO_FLAGS) $(CURRYLIB_PREBUILD_MODULES); \
	  $(PREBUILD_ENV) $(PREFIX)/bin/sprite-make --so $(PREBUILD_SO_FLAGS) $(CURRYLIB_PREBUILD_MODULES) \
	    || exit 1; \
	  $(call PREBUILD_CHECK,.so); \
	  $(call PREBUILD_CHECK,.so.abi); \
	else \
	  echo "Skipping the C++ build of the Curry library:" \
	       "no C++ compiler at $(PREFIX)/tools/cxx."; \
	fi
install:: prebuild
