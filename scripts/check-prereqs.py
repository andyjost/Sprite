#!/usr/bin/env python3
"""Report developer prerequisites; never install or change configuration."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--doc', action='store_true', help='also check documentation packages')
  parser.add_argument('--with-curry-frontend', default=os.environ.get('SPRITE_FRONTEND', ''),
                      help='Curry front end, otherwise searched on PATH')
  parser.add_argument('--with-icurry', default='', help='optional alternative translator')
  args = parser.parse_args()
  missing = sys.version_info < (3, 11, 4)
  print('Python:', sys.version.split()[0], '(requires >=3.11.4)')
  staged_frontend = Path(__file__).resolve().parents[1] / 'install/tools/curry-frontend'
  programs = [('cmake', 'cmake'), ('ninja', 'ninja'), ('C++ compiler', 'g++'),
              ('Curry front end', args.with_curry_frontend or
                shutil.which('pakcs-frontend') or
                (str(staged_frontend) if staged_frontend.exists() else 'curry-frontend'))]
  if args.with_icurry:
    programs.append(('icurry', args.with_icurry))
  for name, program in programs:
    path = shutil.which(program)
    print(name + ':', path or 'MISSING')
    missing |= path is None
    if name == 'cmake' and path:
      version = subprocess.check_output([path, '--version'], text=True).split()[2]
      missing |= tuple(map(int, version.split('.')[:2])) < (3, 24)
      print('  version:', version, '(requires >=3.24)')
  for name in ['json', 'zlib', 'sqlite3'] + (['sphinx', 'sphinx_rtd_theme'] if args.doc else []):
    found = importlib.util.find_spec(name) is not None
    print(name + ':', 'available' if found else 'MISSING')
    missing |= not found
  print('Set SPRITE_FRONTEND or --with-curry-frontend, or put pakcs-frontend on PATH.')
  print('Optional: pakcs (test oracle), icurry (alternative translator), ccache')
  return int(missing)


if __name__ == '__main__':
  sys.exit(main())
