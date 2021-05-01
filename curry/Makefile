SUBMODULES :=
#
# Note: CURRYLIB_FILES is defined in the top-level Make.include.
#
# The subdirectory here in the source tree corresponding to the configured
# version of PAKCS.  The .curry, .icy, and .json* files there.
CURRYLIB_SUBDIR = $(PAKCS_SUBDIR)
CURRYLIB_SRC = $(addprefix $(CURRYLIB_SUBDIR)/,$(CURRYLIB_FILES))
CURRYLIB_ICY = $(CURRYLIB_SRC:.curry=.icy)
CURRYLIB_JSON = $(CURRYLIB_SRC:.curry=.json.z)

# Note: INSTALL_DIR is the root of the Curry library in the installation tree.
# E.g., this is probably $(PREFIX)/curry.
#
# The subdirectory under INSTALL_DIR where the .icy and .json* files will be
# placed.  E.g., $(PREFIX)/curry/.curry/pakcs-3.3.0.
CURRYLIB_INSTALL_SUBDIR = $(INSTALL_DIR)/.curry/$(INTERMEDIATE_SUBDIR)
CURRYLIB_INSTALL_SRC = $(addprefix $(INSTALL_DIR)/,$(CURRYLIB_FILES))
CURRYLIB_INSTALL_ICY = $(addprefix $(CURRYLIB_INSTALL_SUBDIR)/,$(CURRYLIB_FILES:.curry=.icy))
CURRYLIB_INSTALL_JSON = $(addprefix $(CURRYLIB_INSTALL_SUBDIR)/,$(CURRYLIB_FILES:.curry=.json.z))
CURRYLIB_INSTALL_FILES = $(CURRYLIB_INSTALL_SRC) $(CURRYLIB_INSTALL_ICY) $(CURRYLIB_INSTALL_JSON)

# Do not clean via the normal rule because these files are not placed under
# object_root.  The Curry library is special because a fresh download of Sprite
# should contain them.  They are in a cache of sorts, intended to streamline
# installation.
clean-currylib:
	$(call clean_files,$(CURRYLIB_SRC) $(CURRYLIB_ICY) $(CURRYLIB_JSON),rm -f)
	$(call clean_files,$(CURRYLIB_SUBDIR),rmdir)

FILES_TO_UNINSTALL += $(CURRYLIB_INSTALL_FILES)
DIRS_TO_UNINSTALL += $(CURRYLIB_INSTALL_SUBDIR) $(INSTALL_DIR)/.curry

include Make.include

.PHONY: srcs icy json currylib objs

srcs : $(CURRYLIB_SRC)
icy  : $(CURRYLIB_ICY)
json : $(CURRYLIB_JSON)
currylib: srcs icy json

# The sources are needed prior to installation.  Extend target `objs` to
# achieve that.
objs :: srcs
install :: $(CURRYLIB_INSTALL_FILES)

$(CURRYLIB_SUBDIR):
	mkdir -p $@

$(CURRYLIB_INSTALL_SUBDIR):
	mkdir -p $@

$(CURRYLIB_INSTALL_SUBDIR)/% : $(CURRYLIB_SUBDIR)/% | $(CURRYLIB_INSTALL_SUBDIR)
	cp $< $@

$(INSTALL_DIR)/% : $(CURRYLIB_SUBDIR)/% | $(CURRYLIB_INSTALL_SUBDIR)
	cp $< $@

$(CURRYLIB_SUBDIR)/%.curry : %.curry | $(CURRYLIB_SUBDIR)
	@rm -f $@
	ln -s ../$< $@

$(CURRYLIB_SUBDIR)/Prelude.curry : | $(CURRYLIB_SUBDIR)
	echo '{-# LANGUAGE CPP #-}'         >  $@
	echo '#define __KICS2__ 1'          >> $@
	echo                                >> $@
	cat $(PAKCS_HOME)/lib/Prelude.curry >> $@

$(CURRYLIB_SUBDIR)/%.icy : $(CURRYLIB_SUBDIR)/%.curry | $(CURRYLIB_SUBDIR)
	$(PREFIX)/bin/sprite-make --icy $< -o $@

$(CURRYLIB_SUBDIR)/%.json.z : $(CURRYLIB_SUBDIR)/%.curry | $(CURRYLIB_SUBDIR)
	$(PREFIX)/bin/sprite-make --json $< -zc -o $@

