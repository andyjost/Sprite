#!/usr/bin/python
'''Get Curry examples by parsing the public webpage hosted at uni-kiel.'''

# ----------------------- CONFIG --------------------------
INCLUDE = ['funprogs', 'logprogs', 'flprogs']
EXCLUDE = [
    # Exclude GUI programs.  I have not tried them.
    'guicurry', 'tkcurry'
    # These fail with the following error:
    #     ERROR: FlatToICurry found a free variable while making an expression
  , 'escher_perm', 'family_con', 'family_fun', 'family_rel'
    # Other failures.
  , 'prolog'      # Unexpected token `\'
  , 'daVinciTest' # Interface for module DaVinci not found
  , 'iodemo'      # `findfirst' is undefined
  , 'best', 'chords', 'england', 'nats', 'search', 'sportsdb' # uses obsolete 'findall'
  ]
# ---------------------------------------------------------

import collections
import os
import re
import shutil
import subprocess
import glob

import six


# This script should be called from the tests/data/scripts directory.
assert os.path.split(os.getcwd())[-1] == 'scripts'
os.chdir('../curry')

REMOTE_DIR = 'https://www.informatik.uni-kiel.de/~curry/examples/'

# Read the index.
index = collections.defaultdict(set)
current_section = None
subprocess.check_call(['wget', os.path.join(REMOTE_DIR, 'index.html')])
with open('index.html', 'r') as src:
  for line in src.readlines():
    # Capture the categories.
    m_section = re.match(r'<li><a href="#(\w+)">', line)
    if m_section:
      section_name = m_section.group(1)
      if section_name not in EXCLUDE and (not INCLUDE or section_name in INCLUDE):
        index[section_name]
      continue
    del m_section

    # Populate the categories.
    m_head = re.match(r'<h3><a name="(\w+)">', line)
    if m_head:
      section_name = m_head.group(1)
      current_section = section_name if section_name in index else None
      continue
    del m_head

    m_item = re.match(r'<li> <a href="\w+\.curry">(\w+)\.curry</a>', line)
    if m_item and current_section is not None:
      curryfile = m_item.group(1)
      if curryfile not in EXCLUDE:
        index[current_section].add(curryfile)

# Clean up files.
for filename in glob.glob('robots.txt*'):
  os.remove(filename)
for filename in glob.glob('index.html*'):
  os.remove(filename)

with open('../index.py', 'w') as tocfile:
  tocfile.write(str({k:list(v) for k,v in six.iteritems(index)}))

# Get the Curry files.
os.chdir('kiel')
cmd = 'wget -A *.curry -nd -nc --no-parent -r %s' % REMOTE_DIR
subprocess.check_call(cmd.split())

