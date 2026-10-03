'''
A package dependency solver.

Builds a package index in Python, passes it with the root requirements to the
Curry function ``plans``, and prints every consistent plan.  The newest plan
is chosen in Python.

Usage: python go.py [NAME=V1,V2,... ...]      (default: app=1,2)

Each argument is a root requirement: the package NAME and the versions of it
that are acceptable.
'''
import os
import sys
import curry

# Find Deps.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Deps

def text(s):
  '''Converts a Python str to a Curry String.

  A Python str of length one converts to a Char, so pass every String as a
  list of one-character strings.
  '''
  return list(s)

# The package index: (name, version, requirements).  A requirement names a
# package and the versions of it that satisfy the requirement.
INDEX = [
    ('app',  1, [('web', [2, 3]), ('db', [1, 2])]),
    ('app',  2, [('web', [3]),    ('db', [2])]),
    ('web',  1, [('http', [1])]),
    ('web',  2, [('http', [1, 2])]),
    ('web',  3, [('http', [2])]),
    ('db',   1, []),
    ('db',   2, [('http', [1])]),
    ('http', 1, []),
    ('http', 2, []),
  ]

def curry_index(index):
  '''Converts the index to the Curry type Index, one text() per name.'''
  return [
      (text(name), version, [(text(dep), versions) for dep, versions in reqs])
      for name, version, reqs in index
    ]

def parse_root(arg):
  '''Parses NAME=V1,V2 into (NAME, [V1, V2]).'''
  name, sep, versions = arg.partition('=')
  if not sep or not name or not versions:
    raise SystemExit('usage: python go.py [NAME=V1,V2,... ...]')
  return name, [int(v) for v in versions.split(',')]

def format_requirement(req):
  name, versions = req
  return '%s %s' % (name, '|'.join(str(v) for v in versions))

def format_plan(plan):
  return '  '.join('%s %d' % (name, version) for name, version in plan)

def versions(plan):
  '''The version of every package in index order, for sorting.'''
  return [version for _, version in plan]

def main(args):
  roots = [parse_root(arg) for arg in args] or [('app', [1, 2])]
  print('index:')
  for name, version, reqs in INDEX:
    needs = ', '.join(format_requirement(req) for req in reqs)
    print('  %s %d%s' % (name, version, ' needs ' + needs if needs else ''))
  print('roots: ' + '  '.join(format_requirement(root) for root in roots))
  # One call evaluates to every consistent plan.  converter='topython' turns
  # each Curry plan into a Python list of (str, int) pairs.  The order of the
  # values is not promised, so sort them.
  curry_roots = [(text(name), allowed) for name, allowed in roots]
  found = curry.eval(Deps.plans, curry_index(INDEX), curry_roots, converter='topython')
  plans = sorted(found, key=versions)
  print('plans (%d):' % len(plans))
  for plan in plans:
    print('  ' + format_plan(plan))
  if plans:
    print('newest: ' + format_plan(max(plans, key=versions)))
  else:
    print('newest: none')

if __name__ == '__main__':
  main(sys.argv[1:])
