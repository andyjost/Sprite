SUBMODULES := src
DIRS_TO_CLEAN += $(OBJECT_ROOT)
include Make.include

# libs: $(ROOT_DIR)/sprite.a($(OBJECT_ROOT)/memory.o)

ifdef PYTHON_EXECUTABLE
$(PREFIX)/bin:
	mkdir -p $(PREFIX)/bin
$(PREFIX)/bin/python : | $(PREFIX)/bin
	ln -s $(PYTHON_EXECUTABLE) $(PREFIX)/bin/python
$(PREFIX)/bin/coverage : | $(PREFIX)/bin
	ln -s $(PYTHON_COVERAGE_EXECUTABLE) $(PREFIX)/bin/coverage
$(PREFIX)/bin/curry2json : | $(PREFIX)/bin
	ln -s $(CURRY2JSON) $(PREFIX)/bin/curry2json
install: $(PREFIX)/bin/python     \
         $(PREFIX)/bin/coverage   \
         $(PREFIX)/bin/curry2json \
####
uninstall:
	rm $(PREFIX)/bin/python
	rm $(PREFIX)/bin/coverage
	rm $(PREFIX)/bin/curry2json
	rmdir $(PREFIX)/bin
endif
