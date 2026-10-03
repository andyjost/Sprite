RELATIVE_INSTALL_DIR := sysconfig
include Make.include

# The module list is computed from the library directories.  Rebuild it when
# a module is added or removed, or the script changes.
$(INSTALL_DIR)/currylib_module_names: $(ROOT_DIR)/curry/module_names.py \
    $(shell find $(ROOT_DIR)/curry/lib -type d -name .curry -prune -o -type d -print)
