#!/bin/bash
rm -f curry.*.rst curry.*.rst.rej
# The last argument excludes curry.backends.llvm, a package of empty files.
../../../install/bin/sprite-invoke ../../../install/bin/python -m sphinx.ext.apidoc -o . ../../../install/python/curry --module-first --force --separate --no-toc ../../../install/python/curry/backends/llvm
patch -u < patches.txt
