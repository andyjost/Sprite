RELATIVE_INSTALL_DIR := tools
include Make.include

# jq is optional.
ifndef JQ_EXECUTABLE
  LINKS := $(filter-out jq.link,$(LINKS))
endif

