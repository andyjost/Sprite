#!/bin/bash
rm -f curry.*.rst curry.*.rst.rej
../../../install/bin/sprite-invoke ../../../install/bin/python -m sphinx.ext.apidoc -o . ../../../install/python/curry --module-first --force --separate --no-toc
patch -u < patches.txt
