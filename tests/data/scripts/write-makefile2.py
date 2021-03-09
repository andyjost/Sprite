#!/usr/bin/python

import os

# This script should be called from the tests/data/scripts directory.
assert os.path.split(os.getcwd())[-1] == 'scripts'
os.chdir('..')

index = eval(open('index.py', 'r').read())
files = []
for category in index:
	for cyfile in index[category]:
		files.append(cyfile)

with open('Makefile2', 'w') as makefile:
  print >>makefile, '.PHONY : clean json'
  print >>makefile, 'PROGRAMS := %s' % ' '.join(files)
  print >>makefile, 'JSONFILES := $(foreach file,$(PROGRAMS),json/kiel-$(file).json)'
  print >>makefile, ''
  print >>makefile, 'json : $(JSONFILES)'
  print >>makefile, ''
  print >>makefile, 'json/kiel-%.json : curry/kiel/.curry/%.json'
  print >>makefile, '	cp $< $@'
  print >>makefile, ''
  print >>makefile, 'ICURRY := $(shell which ICURRY)'
  print >>makefile, 'ICURRY2JSON := $(shell which ICURRY2JSON)'
  print >>makefile, 'curry/kiel/.curry/%.json : curry/kiel/%.curry $(CURRY2JSON)'
  print >>makefile, '	-$(ICURRY) $<'
  print >>makefile, '	-$(ICURRY2JSON) $< > $@'
  print >>makefile, ''
  print >>makefile, 'clean :'
  print >>makefile, '	rm -f $(JSONFILES)'

