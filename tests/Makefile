# Note: stdbuf is used to unbuffer I/O when tests are run via the vim :make
# command.  This allows interactive code to be added to debug tests.

.PHONY=test
test:
	@stdbuf -i0 -o0 -e0 ./lib/run_tests

.PHONY: test_*.py
test_*.py:
	@stdbuf -i0 -o0 -e0 ./lib/run_tests $@
