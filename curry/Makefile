SUBMODULES :=
DIRS_TO_REC_UNINSTALL += $(INSTALL_DIR)/.curry

# Note: CURRYLIB_FILES defined in top-level Make.include.
SUBDIR = $(PAKCS_SUBDIR)
CURRYLIB_SRC = $(addprefix $(SUBDIR)/,$(CURRYLIB_FILES))
CURRYLIB_ICY = $(CURRYLIB_SRC:.curry=.icy)
CURRYLIB_JSON = $(CURRYLIB_SRC:.curry=.json.z)
FILES_TO_CLEAN += $(CURRYLIB_SRC) $(CURRYLIB_ICY) $(CURRYLIB_JSON)
DIRS_TO_CLEAN += $(SUBDIR)

include Make.include

.PHONY: srcs icy json currylib objs

srcs : $(CURRYLIB_SRC)
icy  : $(CURRYLIB_ICY)
json : $(CURRYLIB_JSON)
currylib: srcs icy json

# The sources are needed prior to installation.
objs :: srcs

$(SUBDIR):
	mkdir -p $@

$(SUBDIR)/%.curry : %.curry | $(SUBDIR)
	@rm -f $@
	ln -s ../$< $@

$(SUBDIR)/Prelude.curry : | $(SUBDIR)
	echo '{-# LANGUAGE CPP #-}'         >  $@
	echo '#define __KICS2__ 1'          >> $@
	echo                                >> $@
	cat $(PAKCS_HOME)/lib/Prelude.curry >> $@

$(SUBDIR)/%.icy : $(SUBDIR)/%.curry | $(SUBDIR)
	$(PREFIX)/bin/sprite-make --icy $< -o $@

$(SUBDIR)/%.json.z : $(SUBDIR)/%.curry | $(SUBDIR)
	$(PREFIX)/bin/sprite-make --json $< -zc -o $@

