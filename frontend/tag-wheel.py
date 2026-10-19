#!/usr/bin/env python3
'''Try auditwheel; validate the ELF floor before the data-only fallback.'''
import argparse
import json
from pathlib import Path
import subprocess
import sys


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('wheel', type=Path)
  parser.add_argument('--info', type=Path, required=True)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  info = json.loads(args.info.read_text())
  tag = 'manylinux_2_28_' + info['architecture']
  args.output.mkdir(parents=True, exist_ok=True)
  result = subprocess.run([
      sys.executable, '-m', 'auditwheel', 'repair', '--plat', tag
    , '--wheel-dir', str(args.output), str(args.wheel)
    ])
  if result.returncode == 0:
    return
  print('auditwheel refused the wheel; checking the data-only fallback.', flush=True)
  floor = info['glibc_required']
  if floor and tuple(map(int, floor.split('.'))) > (2, 28):
    raise SystemExit('Cannot claim manylinux_2_28: ELF needs GLIBC_' + floor
        + '. The unretagged Linux wheel is retained for diagnosis.')
  # package.py rejects dependencies outside the system allowlist and GMP,
  # and vendors GMP with $ORIGIN; it inspects both files for GLIBC versions.
  subprocess.run([
      sys.executable, '-m', 'wheel', 'tags', '--platform-tag', tag
    , str(args.wheel)
    ], check=True)
  tagged = args.wheel.with_name(args.wheel.name.replace('linux_' + info['architecture'], tag))
  import shutil
  shutil.copy2(tagged, args.output / tagged.name)


if __name__ == '__main__':
  main()
