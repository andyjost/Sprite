#!/usr/bin/env python3
"""Portable entry for the test runner; see section 10 of README."""
import os
from pathlib import Path
import subprocess
import sys


def main(argv=None):
  testdir = Path(__file__).resolve().parent
  env = dict(os.environ)
  home = Path(env.get('SPRITE_HOME') or testdir.parent / 'install').resolve()
  if not home.is_dir():
    print('Error: SPRITE_HOME is not a directory.', file=sys.stderr)
    return 1
  suffix = '.dll' if sys.platform == 'win32' else '.dylib' if sys.platform == 'darwin' else '.so'
  if not (home / 'lib' / ('libcurryrt' + suffix)).is_file():
    print('Error: SPRITE_HOME does not point to a staged Sprite runtime.', file=sys.stderr)
    return 1
  env['SPRITE_HOME'] = str(home)
  env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(testdir / 'lib'), env.get('PYTHONPATH')]))
  python = sys.executable if sys.platform == 'win32' else str(home / 'bin' / 'python')
  return subprocess.call([python, '-B', '-m', 'testrunner'] + list(sys.argv[1:] if argv is None else argv),
                         cwd=testdir, env=env)


if __name__ == '__main__':
  sys.exit(main())
