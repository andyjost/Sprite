include Make.include
ifndef PYTHON_PACKAGE_NAME
  $(error PYTHON_PACKAGE_NAME must be defined))
endif
PYTHON_LIB_INSTALL_DIR := $(PREFIX)/lib/python2.7/$(PYTHON_PACKAGE_NAME) 

TOP_TARGETS := install-pylib uninstall-pylib
.PHONY: $(TOP_TARGETS)

install: install-pylib
uninstall: uninstall-pylib

install-pylib: uninstall-pylib
	mkdir -p $(PYTHON_LIB_INSTALL_DIR)
	# Overlay .so and .py files to make the Python package.
	(cd $(OBJECT_ROOT)/python && find . -name '*.so' | xargs tar cf -) | (cd $(PYTHON_LIB_INSTALL_DIR) && tar xf -)
	(cd $(ROOT_DIR)/src/python && find . -name '*.py' | xargs tar cf -) | (cd $(PYTHON_LIB_INSTALL_DIR) && tar xf -)

uninstall-pylib:
	rm -rf $(PYTHON_LIB_INSTALL_DIR)

