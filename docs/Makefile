# Documentation uses the staged package and the tools of its interpreter.
PREFIX ?= $(abspath ../install)
BUILDDIR ?= $(abspath ../object-root/docs)
SPHINXOPTS ?=
SPHINXBUILD ?= $(PREFIX)/bin/python -m sphinx
.DEFAULT_GOAL := all
.NOTPARALLEL:
.PHONY: all html clean help build-module latexpdf info install uninstall
all: html man info
build-module:
	cd source/Reference && ./build-api.bash
	cd source/CommandLineInterface && ./build.bash
html: build-module
	$(SPHINXBUILD) -W --keep-going -b html $(SPHINXOPTS) source $(BUILDDIR)/html
latexpdf: latex
	$(MAKE) -C $(BUILDDIR)/latex all-pdf
info: texinfo
	$(MAKE) -C $(BUILDDIR)/texinfo info
install: all
	$(PREFIX)/bin/python -c 'import shutil; shutil.copytree("$(BUILDDIR)", "$(PREFIX)/docs", dirs_exist_ok=True)'
uninstall:
	rm -rf $(PREFIX)/docs
clean:
	rm -rf $(BUILDDIR)
help:
	@echo 'make html: generate the Reference and command help, then build HTML'
	@echo 'Other Sphinx builders: dirhtml singlehtml latex text man texinfo epub linkcheck'
builders := dirhtml singlehtml pickle json htmlhelp qthelp applehelp devhelp epub latex text man texinfo gettext changes xml pseudoxml linkcheck doctest coverage
.PHONY: $(builders)
$(builders): build-module
	$(SPHINXBUILD) -W --keep-going -b $@ $(SPHINXOPTS) source $(BUILDDIR)/$@
