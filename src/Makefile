SUBMODULES := cyrt python export
# The extension modules under python link against libcyrt.so and build it
# through a second make when it is missing (see python/Make.include).  Two
# makes on one target race under make -j, so python waits for cyrt.  export
# writes links, scripts, and settings only; it runs beside both.
python: | cyrt
include Make.include
DIRS_TO_UNINSTALL += $(PREFIX)/python
