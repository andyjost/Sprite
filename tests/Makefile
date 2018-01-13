# Note: stdbuf is used to unbuffer I/O when tests are run via the vim :make
# command (shortcut is simply <Enter>).  This allows interactive code to be
# added to debug tests and run conveniently from the editor.  socat with
# readline adds history and line-editing features.  On Debian, socat must be
# built from source to enable readline.  The following commands were tested on
# Ubuntu 16.04:
#
#     sudo apt-get build-dep socat
#     sudo apt-get install libreadline-dev
#     apt-get source socat
#     cd socat-1.7.3.1
#     sed -i 's/ -- --disable-readline//' debian/rules
#     dpkg-buildpackage -uc -us
#     cd ..
#     sudo dpkg -i socat_1.7.3.1-1_amd64.deb

.PHONY=test
test:
	@stdbuf -i0 -o0 -e0 socat readline,prompt='>>> ' exec:./run_tests

.PHONY: test_*.py
test_*.py:
	./run_tests $@
