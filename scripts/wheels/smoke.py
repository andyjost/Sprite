#!/usr/bin/env python3
"""Exercise shipped compiled code, and optionally a newly loaded Curry source."""
import argparse
from pathlib import Path
import subprocess
import sys


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
    result = subprocess.run([sys.executable, '-m', 'curry', str(args.peano)],
                            text=True, capture_output=True)
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    assert result.returncode == 0, result.returncode
    assert result.stdout.strip() == 'S (S O)', result


if __name__ == '__main__':
  main()
