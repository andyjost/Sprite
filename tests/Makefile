# Note: stdbuf is used to unbuffer I/O when tests are run via an editor.  In
# vim, the :make command (shortcut: <Enter>) can be used to conveniently
# interleave editing and running tests.  You may wish to update :makeprg so
# that it only runs tests in the file being edited, e.g.  by issuing the
# following command:
#
#     :let &l:makeprg = 'make '.expand('%')
#
# socat with readline adds history and line-editing features, which are useful
# when interacting with tests.  For example, after importing cytest you can say
# breakpoint() in the test code wherever you'd like to get an interactive
# prompt.  With socat+readline useful features such as using the "up" and
# "down" arrow keys to browse command history are available.  On Debian, socat
# must be built from source to enable readline.  The following commands were
# tested on Ubuntu 16.04:
#
#     sudo apt-get build-dep socat
#     sudo apt-get install libreadline-dev
#     apt-get source socat
#     cd socat-1.7.3.1
#     sed -i 's/ -- --disable-readline//' debian/rules
#     dpkg-buildpackage -uc -us
#     cd ..
#     sudo dpkg -i socat_1.7.3.1-1_amd64.deb

.PHONY: test
test:
	./run_tests

.PHONY: unit_*.py
unit_*.py:
	@if (( hash stdbuf 2>/dev/null )); \
		then if (( hash socat 2>/dev/null )); \
			then stdbuf -i0 -o0 -e0 socat readline,prompt='>>> ' exec:"./run_tests $@"; \
			else if (( hash rlwrap 2>/dev/null )); \
				then stdbuf -i0 -o0 -e0 rlwrap ./run_tests $@; \
				else stdbuf -i0 -o0 -e0 ./run_tests $@; \
				fi; \
			fi; \
		else ./run_tests $@; \
		fi;

