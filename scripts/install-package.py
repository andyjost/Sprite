#!/usr/bin/env python3
"""Finish a traditional CMake install using that installation's own tools.

Wheels carry relative stamps and omit the compiler's precompiled headers.
A traditional install retains its absolute stamps and its prepared header.
"""
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile

prefix = Path(sys.argv[1]).resolve()
if len(sys.argv) > 2:
  image = Path(sys.argv[2])
  # CMake's timestamp comparison can retain a stamp rewritten by an old
  # installer in the same clock second. Copy changed content as a whole,
  # including the object it describes, before rewriting any prefixes.
  for source in image.rglob('*'):
    relative = source.relative_to(image)
    if source.is_symlink() or not source.is_file() \
        or any(part.endswith('.gch') for part in relative.parts):
      continue
    target = prefix / relative
    if target.is_file() and target.read_bytes() == source.read_bytes():
      continue
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=target.parent, prefix='.install-')
    os.close(fd)
    try:
      shutil.copy2(source, temporary)
      os.replace(temporary, target)
    finally:
      Path(temporary).unlink(missing_ok=True)
  # A tool the configuration no longer names (icurry after a reconfigure
  # without it) has no link in the image; the install keeps nothing of it.
  tools = image / 'tools'
  if tools.is_dir() and (prefix / 'tools').is_dir():
    present = {entry.name for entry in tools.iterdir()}
    for entry in (prefix / 'tools').iterdir():
      if entry.name not in present and (entry.is_symlink() or entry.is_file()):
        entry.unlink()
for stamp in (prefix / 'curry').rglob('*.so.abi'):
  lines = stamp.read_text().splitlines()
  lines[1] = str(prefix)
  text = '\n'.join(lines) + '\n'
  if stamp.read_text() != text:
    stamp.write_text(text)

env = os.environ.copy()
for name in list(env):
  if name.startswith('SPRITE_') or name in ('CURRYPATH', 'CFLAGS', 'CXXFLAGS'):
    env.pop(name)
env.update(SPRITE_HOME=str(prefix), PYTHONPATH=str(prefix / 'python'))
subprocess.run([sys.executable, '-c', '''
import curry
from curry.backends.cxx.toolchain import Cpp2So
Cpp2So(curry._interpreter_).prepare_header()
'''], env=env, check=True)
