# The environment supplies CMake, a build tool and the build Python.
CMAKE ?= cmake
PYTHON ?= python3
BUILD_DIR ?= object-root/cmake
PREFIX ?= $(CURDIR)/install
JOBS ?= $(shell $(PYTHON) scripts/build-settings.py --jobs "$(BUILD_DIR)/CMakeCache.txt")
CMAKE_ARGS ?=
.DEFAULT_GOAL := default-goal
# An explicit make -jN takes precedence over JOBS.
make_jobs = $(patsubst -j%,%,$(filter -j%,$(MAKEFLAGS)))
effective_jobs = $(if $(filter -j,$(MAKEFLAGS)),auto,$(or $(make_jobs),$(JOBS),1))
.PHONY: default-goal stage all cmake-configure install test overlay overlay-prune overlay-interfaces overlay-archive check-prereqs clean docs
default-goal: stage
	$(MAKE) overlay
stage: all
	$(CMAKE) --install $(BUILD_DIR) --prefix "$(PREFIX)"
all: cmake-configure
	env SPRITE_BUILD_JOBS=$(effective_jobs) $(CMAKE) --build $(BUILD_DIR) $(if $(filter-out auto,$(effective_jobs)),--parallel $(effective_jobs),--parallel)
cmake-configure:
	$(CMAKE) -S . -B $(BUILD_DIR) -G Ninja -DPython_EXECUTABLE="$$(command -v $(PYTHON))" $(CMAKE_ARGS) $(if $(GC),-DGC=$(GC)) $(if $(GC_WRITE_COUNTERS),-DGC_WRITE_COUNTERS=$(GC_WRITE_COUNTERS)) $(if $(COUNTERS),-DCOUNTERS=$(COUNTERS)) $(if $(TRACE),-DTRACE=$(TRACE)) $(if $(SPRITE_REBUILD_ICY),-DSPRITE_REBUILD_ICY=$(SPRITE_REBUILD_ICY)) $(if $(DEBUG),-DCMAKE_BUILD_TYPE=$(if $(filter 1,$(DEBUG)),Debug,Release))
install: stage
test:
	cd tests && ./run_tests
check-prereqs:
	$(PYTHON) scripts/check-prereqs.py
overlay-archive: stage
overlay overlay-prune overlay-interfaces overlay-archive:
	$(PYTHON) scripts/overlay.py $@ $(if $(OVERLAY_ROOT),--root $(OVERLAY_ROOT)) $(if $(OVERLAY_DIR),--directory $(OVERLAY_DIR)) $(if $(V),--verbose)
clean:
	env SPRITE_BUILD_JOBS=$(effective_jobs) $(CMAKE) --build $(BUILD_DIR) --target clean
docs:
	$(MAKE) -C docs html
	$(MAKE) -C docs latexpdf
