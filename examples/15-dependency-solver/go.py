'''
A package dependency solver.

Holds a package index in Python, asks Curry for the preferred plan of the
root requirements, and prints the plan as a lockfile.  When no plan exists,
it asks Curry which requirement breaks the plan and where the search fails.

Usage: python go.py [--index] [--yank NAME=V]... [--lock FILE] [ROOT ...]

A ROOT is NAME=V for one version or NAME=LO..HI for a range of versions.
The default is app=1..2.  --index prints the index first.  --yank marks a
version of the index as yanked.  --lock reads a lockfile that an earlier run
printed, and the versions in it are preferred.

The exit status is 0 with a plan, 1 without one, and 2 for a root that the
index does not know.
'''
import os
import sys
import tomllib
import curry

# Find Deps.curry next to this file, whatever the working directory is.
curry.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curry.lib import Deps

# The package index: (name, version, requirements).  A requirement names a
# package and a range of its versions, both bounds included.  The last entry,
# cli, is not reachable from app.
INDEX = [
    ('app',  1, [('web', (2, 3)), ('db', (1, 2))]),
    ('app',  2, [('web', (3, 3)), ('db', (2, 2))]),
    ('web',  1, [('http', (1, 1))]),
    ('web',  2, [('http', (1, 2))]),
    ('web',  3, [('http', (2, 2))]),
    ('db',   1, []),
    ('db',   2, [('http', (1, 1))]),
    ('http', 1, []),
    ('http', 2, []),
    ('cli',  1, [('web', (1, 1))]),
  ]

def parse_root(arg):
  '''Parses NAME=V or NAME=LO..HI into (NAME, (LO, HI)).'''
  name, sep, versions = arg.partition('=')
  if not sep or not name or not versions:
    raise SystemExit('usage: python go.py [NAME=V | NAME=LO..HI ...]')
  lo, sep, hi = versions.partition('..')
  return name, (int(lo), int(hi if sep else lo))

def parse_pin(arg):
  '''Parses NAME=V into (NAME, V).'''
  name, sep, version = arg.partition('=')
  if not sep or not name or not version.isdigit():
    raise SystemExit('go.py: expected NAME=V, got %r' % arg)
  return name, int(version)

def read_lock(filename):
  '''The versions of a lockfile as (name, version) pairs.'''
  with open(filename, 'rb') as stream:
    tables = tomllib.load(stream).get('package', [])
  return [(table['name'], table['version']) for table in tables]

def show_range(lo_hi):
  lo, hi = lo_hi
  return str(lo) if lo == hi else '%d..%d' % (lo, hi)

def show_requirement(req):
  name, versions = req
  return '%s %s' % (name, show_range(versions))

def show_pin(pin):
  return '%s %d' % pin

def chain(pin, trace):
  '''The way from the roots to a chosen version: "app 2 > web 3".'''
  by = dict(trace)
  names = []
  while pin[0]:
    names.append(show_pin(pin))
    pin = by[pin]
  return ' > '.join(reversed(names)) or 'the roots'

def lockfile(plan):
  '''The plan as a lockfile: one table per package, in the order of the
  names, each with the versions it depends on.'''
  chosen = dict(plan)
  lines = []
  for name, version in sorted(plan):
    reqs = next(curry.eval(Deps.requires, INDEX, (name, version),
                           converter='topython'))
    deps = ['%s %d' % (dep, chosen[dep]) for dep, _ in reqs]
    lines += ['[[package]]', 'name = "%s"' % name, 'version = %d' % version]
    if deps:
      lines.append('dependencies = [%s]'
                   % ', '.join('"%s"' % dep for dep in deps))
    lines.append('')
  return '\n'.join(lines)

def solvable(index, yanked, lock, roots):
  '''True when the roots have a plan over the index.'''
  return next(curry.eval(Deps.solvable, index, yanked, lock, roots,
                         converter='topython'))

def explain(yanked, lock, roots):
  '''Prints why the roots have no plan: the requirements whose deletion
  restores one, and the first violation of each branch of the search.'''
  # The cheap explanation.  Delete one requirement at a time, in Python, and
  # ask Curry whether a plan exists without it.  A lone root is the question
  # itself, so the roots count only when there are several.
  culprits = []
  if len(roots) > 1:
    for i, root in enumerate(roots):
      if solvable(INDEX, yanked, lock, roots[:i] + roots[i + 1:]):
        culprits.append('the root ' + show_requirement(root))
  for i, (name, version, reqs) in enumerate(INDEX):
    for j, req in enumerate(reqs):
      entry = (name, version, reqs[:j] + reqs[j + 1:])
      if solvable(INDEX[:i] + [entry] + INDEX[i + 1:], yanked, lock, roots):
        culprits.append('%s %d needs %s'
                        % (name, version, show_requirement(req)))
  if culprits:
    print('a plan exists without any one of these requirements:')
    for culprit in culprits:
      print('  ' + culprit)
  # The better explanation.  Every branch of the search ends in a violation,
  # and every violation is one value of conflict.  The order of the values is
  # not promised, so sort them.
  conflicts = curry.eval(Deps.conflict, INDEX, yanked, lock, roots,
                         converter='topython')
  lines = set()
  for (req, by), clash, trace in conflicts:
    name, (lo, hi) = req
    # The requirer of a root demand is ("", 0), and chain names it "the
    # roots", a plural.
    line = '%s need%s %s' % (
        chain(by, trace), '' if not by[0] else 's', show_requirement(req))
    if clash:
      version, by = clash[0]
      line += ', but %s picked %s %d' % (chain(by, trace), name, version)
    elif any(n == name and lo <= v <= hi for n, v, _ in INDEX):
      line += ', and every such version is yanked'
    else:
      line += ', and the index has no such version'
    lines.add(line)
  print('every branch of the search ends in a conflict:')
  for line in sorted(lines):
    print('  ' + line)

def main(args):
  yanked, lock, roots, show_index = [], [], [], False
  while args:
    arg = args.pop(0)
    if arg == '--index':
      show_index = True
    elif arg == '--yank':
      yanked.append(parse_pin(args.pop(0)))
    elif arg == '--lock':
      lock = read_lock(args.pop(0))
    else:
      roots.append(parse_root(arg))
  roots = roots or [('app', (1, 2))]
  if show_index:
    print('index:')
    for name, version, reqs in INDEX:
      needs = ', '.join(show_requirement(req) for req in reqs)
      print('  %s %d%s' % (name, version, ' needs ' + needs if needs else ''))
  print('roots: ' + ', '.join(show_requirement(root) for root in roots))
  if yanked:
    print('yanked: ' + ', '.join(show_pin(pin) for pin in yanked))
  if lock:
    print('locked: ' + ', '.join(show_pin(pin) for pin in lock))
  # A root that the index does not know is a mistake in the question, not a
  # plan that does not exist.  Ask before the search.
  unknown = next(curry.eval(Deps.unknown, INDEX, roots, converter='topython'))
  if unknown:
    print('no such package: ' + ', '.join(unknown))
    return 2
  # One call.  curry.eval converts the nested tuples, lists, strs and ints of
  # the index, the pins and the roots by the parameter types of preferred;
  # converter='topython' turns the plan into a list of (str, int) pairs.
  # preferred is deterministic, so the generator has one value or none.
  plan = next(curry.eval(Deps.preferred, INDEX, yanked, lock, roots,
                         converter='topython'), None)
  if plan is None:
    print('no plan')
    explain(yanked, lock, roots)
    return 1
  print('plan: ' + ', '.join(show_pin(pin) for pin in plan))
  print(lockfile(plan))
  return 0

if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
