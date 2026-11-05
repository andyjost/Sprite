#!/usr/bin/env python3
"""Select explicit test-data generators in a private CurryCheck 4.0.0.

Sprite uses the existing PAKCS generator route rather than the route that
requires strong enumeration of unknown values. Package properties stay
unchanged. Prelude data declarations are read from its public interface.
This preparation is only for the CPM index test framework.
"""
import argparse
import json
import os
from pathlib import Path


BEFORE = 'if isPAKCS || useUserDefinedGen t || isFloatType t'
AFTER = 'if isPAKCS || curryCompiler == "sprite" || useUserDefinedGen t || isFloatType t'

TYPE_BEFORE = "fprog <- readFlatCurry mn"
TYPE_AFTER = 'fprog <- if curryCompiler == "sprite" && mn == preludeName\n                         then readFlatCurryFile (installDir </> "curry" </> ".curry" </>\n                           "sprite-pakcs-3.10.0" </> "Prelude.fint")\n                         else readFlatCurry mn'


def prepare(project):
  project = Path(project).resolve()
  if Path(os.environ['HOME']).resolve() not in project.parents:
    raise ValueError('the framework checkout must be inside the private CPM home')
  manifest = json.loads((project / 'package.json').read_text())
  if (manifest.get('name'), manifest.get('version')) != ('currycheck', '4.0.0'):
    raise ValueError('expected the pinned CurryCheck 4.0.0 framework')
  source = project / 'src/CurryCheck.curry'
  text = source.read_text()
  changed = False
  for before, after in ((BEFORE, AFTER), (TYPE_BEFORE, TYPE_AFTER)):
    if text.count(after) == 1 and before not in text:
      continue
    if text.count(before) != 1 or after in text:
      raise ValueError('unsupported CurryCheck framework source')
    text = text.replace(before, after)
    changed = True
  if changed:
    source.write_text(text)
  return changed


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('project', type=Path)
  args = parser.parse_args()
  print('Prepared explicit generators.' if prepare(args.project) else
        'Explicit generators already prepared.')


if __name__ == '__main__':
  main()
