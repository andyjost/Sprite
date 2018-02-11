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

with open('Makefile.json', 'w') as makefile:
  print >>makefile, 'JSONFILES := %s' % ' '.join(files)
  print >>makefile, 'json : $(foreach cyfile,$(JSONFILES),json/$(cyfile).json)'
  print >>makefile, 'json/%.json : curry/.curry/%.json'
  print >>makefile, '\tmv $< $@'
  print >>makefile, '\techo rm $**'
  print >>makefile, 'curry/.curry/%.json : curry/%.curry'
  print >>makefile, '\t-../../CMC/translator/bin/curry2json $<'


