SUBMODULES :=
DIRS_TO_REC_UNINSTALL += $(INSTALL_DIR)/.curry
include Make.include

CURRYLIB_SOURCE := $(wildcard *.curry)
CURRYLIB_ICY := $(CURRYLIB_SOURCE:.curry=.icy)
CURRYLIB_JSON := $(CURRYLIB_SOURCE:.curry=.json.z)

# The ICY and JSON files of the Curry library can be prebuilt and checked in to
# streamline the installation process.  Otherwise, they are built the first
# time Sprite runs (which can take several minutes).  To update these files,
# first install Sprite.  Then build the target "currylib" with PREFIX referring
# to the installation, and, finally, check in the new files.  To install the
# new library over an existing one, use "make uninstall install".

%.icy : %.curry
	$(PREFIX)/bin/sprite-make --icy $< -o $@

%.json.z : %.curry
	$(PREFIX)/bin/sprite-make --json $< -zc -o $@

currylib: $(CURRYLIB_ICY) $(CURRYLIB_JSON)

