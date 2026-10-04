RELATIVE_INSTALL_DIR := tools
include Make.include

# icurry, the Curry front end, and PAKCS are optional.  The link rule in
# Make.rules skips a link whose target is empty.  (A change to LINKS here
# would come too late: Make.rules has read the list by now.)

# With ccache (CCACHE in Make.config, configure --with-ccache), tools/cxx is
# a script that runs ccache in front of the post-install compiler, not a
# link to the compiler.  ccache reads the compiler from its command line, so
# the name cxx hides nothing from it.  This explicit rule wins over the link
# rule of Make.rules.  The old entry goes first: a write through a link
# named cxx would write into the compiler.  The script is written beside its
# place and moved in, so no half-written script is ever run.
ifneq ($(strip $(CCACHE)),)
ifneq ($(strip $(CXX_POSTINSTALL)),)
$(INSTALL_DIR)/cxx: cxx.link $(ROOT_DIR)/Make.config
	@mkdir -p $(dir $@)
	rm -f $@ $@.tmp
	printf '%s\n' '#!/bin/sh' \
	    '# Written by make (configure --with-ccache): ccache in front of the' \
	    '# post-install compiler of Sprite.' \
	    'exec "$(CCACHE)" "$(CXX_POSTINSTALL)" "$$@"' > $@.tmp
	chmod 755 $@.tmp
	mv -f $@.tmp $@
endif
endif
