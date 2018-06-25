SUBMODULES := src
DIRS_TO_CLEAN += $(OBJECT_ROOT)
include Make.include

# libs: $(ROOT_DIR)/sprite.a($(OBJECT_ROOT)/memory.o)

ifdef PYTHON_EXECUTABLE
$(PREFIX)/bin:
	mkdir -p $(PREFIX)/bin
$(PREFIX)/.bin:
	mkdir -p $(PREFIX)/.bin
$(PREFIX)/.bin/python : | $(PREFIX)/.bin
	ln -s $(PYTHON_EXECUTABLE) $@
$(PREFIX)/bin/.invoker : $(ROOT_DIR)/scripts/invoker | $(PREFIX)/bin
	cp $< $@
$(PREFIX)/bin/python : | $(PREFIX)/bin
	ln -s $(PREFIX)/bin/.invoker $@
$(PREFIX)/bin/coverage : | $(PREFIX)/bin
	ln -s $(PREFIX)/bin/.invoker $@
$(PREFIX)/.bin/coverage : | $(PREFIX)/.bin
	ln -s $(PYTHON_COVERAGE_EXECUTABLE) $@
$(PREFIX)/bin/curry2json : | $(PREFIX)/bin
	ln -s $(CURRY2JSON) $@

$(PREFIX)/lib:
	mkdir -p $(PREFIX)/lib
$(PREFIX)/lib/curry : | $(PREFIX)/lib
	mkdir -p $(PREFIX)/lib/curry
$(PREFIX)/lib/curry/Prelude.curry : $(ROOT_DIR)/currylib/Prelude.curry | $(PREFIX)/lib/curry
	cp $< $@
$(PREFIX)/lib/curry/.curry/Prelude.json : $(PREFIX)/lib/curry/Prelude.curry \
                                          $(PREFIX)/bin/python
	@echo "****** Compiling the Prelude.  This may take a few minutes. ******"
	$(PREFIX)/bin/python -c 'import curry; curry.compile("goal=True")'

$(ROOT_DIR)/install:
	ln -s $(PREFIX) $@

install: $(PREFIX)/.bin/coverage                 \
         $(PREFIX)/bin/coverage                  \
         $(PREFIX)/bin/curry2json                \
         $(PREFIX)/bin/.invoker                  \
         $(PREFIX)/.bin/python                   \
	       $(PREFIX)/bin/python                    \
         $(PREFIX)/lib/curry/Prelude.curry       \
         $(PREFIX)/lib/curry/.curry/Prelude.json \
  ####
ifneq ($(PREFIX),python)
install: $(ROOT_DIR)/install
endif

uninstall:
	-rm $(PREFIX)/.bin/coverage
	-rm $(PREFIX)/bin/coverage
	-rm $(PREFIX)/bin/curry2json
	-rm $(PREFIX)/bin/.invoker
	-rm $(PREFIX)/.bin/python
	-rm $(PREFIX)/bin/python
	-rm $(PREFIX)/lib/curry/Prelude.curry
	-rm -rf $(PREFIX)/lib/curry/.curry/*
	-rmdir $(PREFIX)/bin
	-rmdir $(PREFIX)/.bin
	-rmdir $(PREFIX)/lib/curry/.curry
	-rmdir $(PREFIX)/lib/curry
	-rmdir $(PREFIX)/lib
	-rmdir $(ROOT_DIR)/install
endif
