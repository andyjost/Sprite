SUBMODULES :=
include Make.include

# .DEFAULT_GOAL = json
# # .SECONDARY:
# .DELETE_ON_ERROR:
# .PHONY: json
#
# CURRYFILES = $(wildcard *.curry)
# JSONFILES = $(patsubst %.curry,.curry/%.json.gz,$(CURRYFILES))
# CURRYLIB_CURRYFILES = $(addprefix \
#     $(PREFIX)/lib/curry/,         \
#     $(notdir $(CURRYFILES))       \
#   )
# CURRYLIB_JSONFILES = $(addprefix \
#     $(PREFIX)/lib/curry/.curry/, \
#     $(notdir $(JSONFILES))       \
#   )
# CURRYLIB_OTHER_FILES = $(CURRYLIB_JSONFILES:.json=.*)
#
# $(PREFIX)/lib/curry/%.curry: %.curry | $(PREFIX)/lib/curry
# 	cp $< $@
#
# .curry/%.json.gz : %.curry $(OBJECT_ROOT)/export/bin/cy2json
# 	$(PYTHON) $(OBJECT_ROOT)/export/bin/cy2json $(basename $*)
#
# # JSON is used as an indicator.  Copy all files with a matching stem.
# $(PREFIX)/lib/curry/.curry/%.json.gz: .curry/%.json.gz | $(PREFIX)/lib/curry/.curry
# 	cp $(basename $<).* $(dir $@)
#
# json : $(JSONFILES)
#
# # No rules for clean.  The JSON files are too expensive to generate every time.
# clean:
# 	@echo 1>&2 Use clean-json to remove JSON files from currylib.
#
# clean-json:
# 	rm -rf .curry
#
# # install: $(CURRYLIB_CURRYFILES) $(CURRYLIB_JSONFILES)
#
# uninstall:
# 	-rm -f $(CURRYLIB_CURRYFILES)
# 	# -rm -rf $(PREFIX)/lib/curry/.curry/*
# 	-rm -rf $(CURRYLIB_OTHER_FILES)
# 	-if [ -d $(PREFIX)/lib/curry/.curry ]; then rmdir $(PREFIX)/lib/curry/.curry; fi
# 	-if [ -d $(PREFIX)/lib/curry ];        then rmdir $(PREFIX)/lib/curry;        fi
#
#
