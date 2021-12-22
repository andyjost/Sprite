#!/bin/bash
rm curry.*.rst
../../../install/bin/sprite-invoke `which sphinx-apidoc` -o . ../../../install/python/curry --module-first --force --separate --no-toc
patch -u < patches.txt
