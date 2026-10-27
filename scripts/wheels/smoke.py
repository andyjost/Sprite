#!/usr/bin/env python3
"""Exercise shipped compiled code, and optionally a newly loaded Curry source."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--peano', type=Path)
  args = parser.parse_args()
  import curry
  from curry.backends.cxx.toolchain import Cpp2So
  from curry.lib import Prelude
  assert curry.config.cxx_compiler(), 'Missing build compiler record'
  prelude = Path(curry.config.prefix()) / 'curry/.curry' / curry.config.intermediate_subdir() / 'Prelude.so'
  assert prelude.is_file(), prelude
  assert Cpp2So(curry._interpreter_).stamp_is_current(str(prelude))
  assert list(curry.eval(Prelude.id(42))) == [42]
  if args.peano:
    with tempfile.TemporaryDirectory() as directory:
      # A copy: the compile leaves no products in the checkout, and every
      # interpreter of a build matrix compiles the program afresh.
      source = Path(directory) / args.peano.name
      shutil.copy(args.peano, source)
      expect(source, 'S (S O)')
      # A program with type classes. Its FlatCurry names the dictionaries
      # of the Prelude in the spelling of the front end that compiled it,
      # which the pinned library (front end 3.1.0) must share; Peano, which
      # has no class, loads under a front end of the other pair as well.
      classes = Path(directory) / 'Classes.curry'
      classes.write_text(CLASSES)
      expect(classes, '"3False[Red,Green]"')


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
