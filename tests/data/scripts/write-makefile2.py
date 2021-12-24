#!/usr/bin/python

from __future__ import print_function
import os, sys

print("This script is obsolete because it uses ICURRY2JSON.")
sys.exit(1)

# This script should be called from the tests/data/scripts directory.
assert os.path.split(os.getcwd())[-1] == 'scripts'
os.chdir('..')

index = eval(open('index.py', 'r').read())
files = []
for category in index:
	for cyfile in index[category]:
		files.append(cyfile)

with open('Makefile2', 'w') as makefile:
  print('.PHONY : clean json', file=makefile)
  print >>makefile, 'PROGRAMS := %s' % ' '.join(files)
  print('JSONFILES := $(foreach file,$(PROGRAMS),json/kiel-$(file).json)', file=makefile)
  print('', file=makefile)
  print('json : $(JSONFILES)', file=makefile)
  print('', file=makefile)
  print('json/kiel-%.json : curry/kiel/.curry/%.json', file=makefile)
  print('	cp $< $@', file=makefile)
  print('', file=makefile)
  print('ICURRY := $(shell which ICURRY)', file=makefile)
  print('ICURRY2JSON := $(shell which ICURRY2JSON)', file=makefile)
  print('curry/kiel/.curry/%.json : curry/kiel/%.curry $(CURRY2JSON)', file=makefile)
  print('	-$(ICURRY) $<', file=makefile)
  print('	-$(ICURRY2JSON) $< > $@', file=makefile)
  print('', file=makefile)
  print('clean :', file=makefile)
  print('	rm -f $(JSONFILES)', file=makefile)

