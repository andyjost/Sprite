SUBMODULES := src
DIRS_TO_CLEAN += $(OBJECT_ROOT)
include Make.include

# libs: $(ROOT_DIR)/sprite.a($(OBJECT_ROOT)/memory.o)

ifdef PYTHON_EXECUTABLE
$(PREFIX)/bin:
	mkdir -p $(PREFIX)/bin
$(PREFIX)/bin/python : | $(PREFIX)/bin
	ln -s $(PYTHON_EXECUTABLE) $(PREFIX)/bin/python
install: $(PREFIX)/bin/python
uninstall:
	rm $(PREFIX)/bin/python
	rmdir $(PREFIX)/bin
endif
