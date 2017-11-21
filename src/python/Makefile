include Make.include


# TOP_TARGETS := install-pylib uninstall-pylib
# .PHONY: $(TOP_TARGETS)
# 
# install: install-pylib
# uninstall: uninstall-pylib
# 
# install-pylib: require-prefix uninstall-pylib
# 	$(MAKE) all # Making 'all' a prerequisite has no effect.  Don't know why.
# 	mkdir -p $(PYTHON_LIB_INSTALL_DIR)
# 	# Overlay .so and .py files to make the Python package.
# 	(cd $(OBJECT_ROOT)/python && find . -name '*.so' | xargs tar cf -) | (cd $(PYTHON_LIB_INSTALL_DIR) && tar xf -)
# 	(cd $(ROOT_DIR)/src/python && find . -name '*.py' | xargs tar cf -) | (cd $(PYTHON_LIB_INSTALL_DIR) && tar xf -)
# 
# uninstall-pylib: require-prefix
# 	-rm -rf $(PYTHON_LIB_INSTALL_DIR)
# 
