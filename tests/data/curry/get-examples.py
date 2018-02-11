#!/usr/bin/python
'''Get Curry examples by parsing the public webpage hosted at uni-kiel.'''

# ----------------------- CONFIG --------------------------
INCLUDE = ['funprogs']
EXCLUDE = ['guicurry', 'tkcurry']
# ---------------------------------------------------------

import collections
import os
import re
import shutil
import subprocess
import glob

REMOTE_DIR = 'https://www.informatik.uni-kiel.de/~curry/examples/'

# Read the classification info.
toc = collections.defaultdict(set)
current_section = None
subprocess.check_call(['wget', os.path.join(REMOTE_DIR, 'index.html')])
with open('index.html', 'r') as src:
  for line in src.readlines():
    # Capture the categories.
    m_section = re.match(r'<li><a href="#(\w+)">', line)
    if m_section:
      section_name = m_section.group(1)
      if section_name not in EXCLUDE and (not INCLUDE or section_name in INCLUDE):
        toc[section_name]
      continue
    del m_section

    # Populate the categories.
    m_head = re.match(r'<h3><a name="(\w+)">', line)
    if m_head:
      section_name = m_head.group(1)
      if section_name in toc:
        current_section = section_name
      continue
    del m_head

    m_item = re.match(r'<li> <a href="\w+\.curry">(\w+\.curry)</a>', line)
    if m_item and current_section is not None:
      curryfile = m_item.group(1)
      toc[current_section].add(curryfile)

# Get the Curry files.
cmd = 'wget -A *.curry -nd -nc --no-parent -r %s' % REMOTE_DIR
subprocess.check_call(cmd.split())

# Organize them according to the table of contents.
for section in toc:
  try:
    os.makedirs(section)
  except OSError:
    pass
  for item in toc[section]:
    shutil.move(item, os.path.join(section, item))

# Clean up the remaining files.
for filename in glob.glob('*.curry'):
  os.remove(filename)
for filename in glob.glob('robots.txt*'):
  os.remove(filename)


