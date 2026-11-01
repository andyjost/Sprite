#!/usr/bin/env python3
"""Exercise shipped compiled code, the JIT, and optionally a newly loaded Curry source."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--peano', type=Path)
  parser.add_argument('--compile', action='store_true')
  parser.add_argument('--jit', action='store_true',
      help='the bitcode of the JIT helpers ships; with llvmlite, a child compiles a hot function')
  args = parser.parse_args()
  import curry
  from curry.lib import Prelude
  from curry.backends.cxx.toolchain import Cpp2So
  if 'SPRITE_INTERPRETER_FLAGS' not in os.environ:
    # The default of every platform; the workflow runs this script again
    # with interpret:off after it compiled the program.
    assert curry.flags['interpret'] == 'new', curry.flags
  assert curry.config.cxx_compiler(), 'Missing build compiler record'
  prelude = Path(curry.config.prefix()) / 'curry/.curry' / curry.config.intermediate_subdir() / ('Prelude' + curry.config.module_object_suffix())
  assert prelude.is_file(), prelude
  assert Cpp2So(curry._interpreter_).stamp_is_current(str(prelude))
  from curry.objects.handle import getHandle
  assert getHandle(Prelude).icurry.metadata.get('cxx.shlib') is not None
  assert list(curry.eval(Prelude.id(42))) == [42]
  if args.jit:
    check_jit(curry)
  if args.peano:
    with tempfile.TemporaryDirectory() as directory:
      # A copy: the compile leaves no products in the checkout, and every
      # interpreter of a build matrix compiles the program afresh.
      source = Path(directory) / args.peano.name
      shutil.copy(args.peano, source)
      if args.compile:
        subprocess.run([sys.executable, '-m', 'curry.tools.make', '--so', str(source)], check=True)
        assert (source.parent / '.curry' / curry.config.intermediate_subdir() / (source.stem + curry.config.module_object_suffix())).is_file()
      expect(source, 'S (S O)')
      # A program with type classes. Its FlatCurry names the dictionaries
      # of the Prelude in the spelling of the front end that compiled it,
      # which the pinned library (front end 3.1.0) must share; Peano, which
      # has no class, loads under a front end of the other pair as well.
      classes = Path(directory) / 'Classes.curry'
      classes.write_text(CLASSES)
      expect(classes, '"3False[Red,Green]"')


def check_jit(curry):
  """The installation has the bitcode of the JIT helpers; with llvmlite, the hot tier compiles."""
  bitcode = curry.config.jit_bitcode()
  assert bitcode and Path(bitcode).is_file(), \
      'the installation has no bitcode of the JIT helpers (lib/curryrt-helpers.bc)'
  print('JIT helpers:', bitcode)
  try:
    import llvmlite
  except ImportError:
    print('llvmlite is not installed; the check of the JIT stops at the bitcode')
    return
  print('llvmlite', llvmlite.__version__)
  # A child: the flags are read at import, and the Prelude must run interpreted
  # for one of its functions to become hot. A local stage has the library's
  # cache, and then the code links from it instead; a wheel ships no cache.
  env = dict(os.environ, SPRITE_INTERPRETER_FLAGS='interpret:all,jit:hot,jit_backend:llvm',
             SPRITE_JIT_THRESHOLD='20')
  result = subprocess.run([sys.executable, '-c', HOT], env=env, capture_output=True, text=True)
  print(result.stdout, end='')
  print(result.stderr, end='', file=sys.stderr)
  assert result.returncode == 0, 'the LLVM JIT failed'


HOT = """\
import time
import curry
from curry.lib import Prelude
from curry.backends.cxx import llvmjit
assert llvmjit.available(), llvmjit._reason
print(curry.eval(Prelude.elem(999999, Prelude.enumFromTo(1, 1000000))).one())
deadline = time.monotonic() + 60
def compiled():
  stats = llvmjit.statistics()
  return stats['hot'] + stats['linked'] > 0
while not compiled() and time.monotonic() < deadline:
  time.sleep(0.05)
stats = llvmjit.statistics()
print('jit:', stats)
assert stats['errors'] == 0, stats['last_error']
assert compiled(), 'the LLVM JIT compiled and linked nothing'
"""


CLASSES = """\
data Color = Red | Green deriving (Eq, Show)

main :: String
main = show (1 + 2 :: Int) ++ show (Red == Green) ++ show [Red, Green]
"""


def expect(source, value):
  """Load a Curry source with python -m curry; its one value must print as given."""
  result = subprocess.run([sys.executable, '-m', 'curry', str(source)],
                          text=True, capture_output=True)
  print(result.stdout, end='')
  print(result.stderr, end='', file=sys.stderr)
  assert result.returncode == 0, (source.name, result.returncode)
  assert result.stdout.strip() == value, (source.name, result.stdout, value)


if __name__ == '__main__':
  main()
