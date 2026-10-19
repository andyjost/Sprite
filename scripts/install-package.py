#!/usr/bin/env python3
"""Finish a traditional CMake install using that installation's own tools.

Wheels carry relative stamps and omit the compiler's precompiled headers.
A traditional install retains its absolute stamps and its prepared header.
"""
import os
from pathlib import Path
import subprocess
import sys

prefix = Path(sys.argv[1]).resolve()
for stamp in (prefix / 'curry').rglob('*.so.abi'):
  digest = stamp.read_text().splitlines()[0]
  text = '%s\n%s\n' % (digest, prefix)
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
