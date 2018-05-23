SUBMODULES := src
DIRS_TO_CLEAN += $(OBJECT_ROOT)
include Make.include

# libs: $(ROOT_DIR)/sprite.a($(OBJECT_ROOT)/memory.o)

ifdef PYTHON_EXECUTABLE
$(PREFIX)/bin:
	mkdir -p $(PREFIX)/bin
$(PREFIX)/bin/.python : | $(PREFIX)/bin
	ln -s $(PYTHON_EXECUTABLE) $@
$(PREFIX)/bin/python : | $(PREFIX)/bin
	cp $(ROOT_DIR)/scripts/python $@
$(PREFIX)/bin/coverage : | $(PREFIX)/bin
	ln -s $(PYTHON_COVERAGE_EXECUTABLE) $@
$(PREFIX)/bin/curry2json : | $(PREFIX)/bin
	ln -s $(CURRY2JSON) $@

$(PREFIX)/lib:
	mkdir -p $(PREFIX)/lib
$(PREFIX)/lib/curry : | $(PREFIX)/lib
	mkdir -p $(PREFIX)/lib/curry
$(PREFIX)/lib/curry/Prelude.curry : | $(PREFIX)/lib/curry
	cp $(ROOT_DIR)/currylib/Prelude.curry $(PREFIX)/lib/curry/Prelude.curry

$(ROOT_DIR)/install:
	ln -s $(PREFIX) $@

install: $(PREFIX)/bin/python              \
         $(PREFIX)/bin/.python             \
         $(PREFIX)/bin/coverage            \
         $(PREFIX)/bin/curry2json          \
         $(PREFIX)/lib/curry/Prelude.curry \
  ####
ifneq ($(PREFIX),python)
install: $(ROOT_DIR)/install
endif

uninstall:
	rm $(PREFIX)/bin/python
	rm $(PREFIX)/bin/.python
	rm $(PREFIX)/bin/coverage
	rm $(PREFIX)/bin/curry2json
	rm $(PREFIX)/lib/curry/Prelude.curry
	rmdir $(PREFIX)/bin
	rmdir $(PREFIX)/lib/curry
	-rm $(ROOT_DIR)/install
endif
