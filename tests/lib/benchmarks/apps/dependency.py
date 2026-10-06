'''
The child program of the dependency item of the applications suite.

Usage: python dependency.py SIDE SIZE CASE

SIDE is ``sprite`` or ``resolvelib``, SIZE the number of packages of the
generated index (see depindex.py), and CASE ``solvable`` or ``unsolvable``.

Both sides answer one question: a plan of the root under the same
preference of the candidates, newest first, or the answer that no plan
exists.  The Sprite side imports the Curry module of example 15
(examples/15-dependency-solver, Deps.curry) and asks ``preferred`` with no
yanked versions and no lockfile, as the driver of the example does; it
resolves the demands in the order it meets them.  The resolvelib side runs
the resolver of pip (the package resolvelib) with a provider over the same
index whose ``find_matches`` lists the versions newest first.  The provider
orders the open requirements as the example provider of resolvelib does,
the package with the fewest candidates first, and resolvelib backjumps to
the cause of a conflict.  So the two sides agree on whether a plan exists,
and each side's plan holds (depindex.holds), but the plans are the same
only when the orders of the two searches agree: in the committed record
they agree at 10 and 20 packages and differ at 50.  The index is built
before the clock starts.  The measured time, ``solve``, covers the
conversion of the index across the boundary (the Sprite side) or the
tables of the provider (the resolvelib side) and the search to its answer.

The program prints one JSON object: the side, the size, the case, the
seconds of ``setup`` (the imports) and ``solve``, ``found``, the plan on the
closure of the root as one line (``plan``), the number of packages of the
closure, the counts of the index, and the fields of curry.stats() on the
Sprite side.  When the resolvelib side cannot import the package, it
prints the object with ``error`` set and exits with status 3; the harness
skips the item before it gets there.
'''

import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LIBDIR = os.path.dirname(os.path.dirname(HERE))
ROOTDIR = os.path.dirname(os.path.dirname(LIBDIR))
EXAMPLE = os.path.join(ROOTDIR, 'examples', '15-dependency-solver')
if LIBDIR not in sys.path:
  sys.path.insert(0, LIBDIR)

from benchmarks.apps import depindex

# The status of the child when resolvelib cannot be imported.
MISSING_STATUS = 3
# A bound on the rounds of resolvelib.  The unsolvable index of 800 packages
# reaches it: resolvelib raises ResolutionTooDeep after seven to eight
# minutes, and the record holds the item as failed (results/README.md).
MAX_ROUNDS = 1000000


def sprite(index, roots):
  '''
  The Sprite side: the first preferred plan of example 15's solver, as its
  driver asks it.  Returns the plan as a dict, or None, and the setup
  seconds.
  '''
  start = time.perf_counter()
  import curry
  curry.path.insert(0, EXAMPLE)
  from curry.lib import Deps
  setup = time.perf_counter() - start
  start = time.perf_counter()
  values = curry.eval(
      Deps.preferred, index, [], [], roots, converter='topython'
    )
  plan = next(values, None)
  solve = time.perf_counter() - start
  report = {'setup': setup, 'solve': solve, 'stats': dict(curry.stats())}
  return None if plan is None else dict(plan), report


class _Candidate:
  __slots__ = ('name', 'version', 'requirements')

  def __init__(self, name, version, requirements):
    self.name = name
    self.version = version
    self.requirements = requirements


class _Requirement:
  __slots__ = ('name', 'low', 'high')

  def __init__(self, name, low, high):
    self.name = name
    self.low = low
    self.high = high


def make_provider(index, AbstractProvider):
  '''
  A provider of resolvelib over an index of the shape of example 15.  The
  candidates of a package are listed newest first, the preference of the
  example; a requirement is satisfied by a version within its range.
  '''
  class Provider(AbstractProvider):
    def __init__(self):
      self.candidates = {}
      for name, version, reqs in index:
        self.candidates.setdefault(name, []).append(_Candidate(
            name, version, [_Requirement(n, lo, hi) for n, (lo, hi) in reqs]
          ))
      for candidates in self.candidates.values():
        candidates.sort(key=lambda c: -c.version)

    def identify(self, requirement_or_candidate):
      return requirement_or_candidate.name

    def get_preference(
        self, identifier, resolutions, candidates, information
      , backtrack_causes
      ):
      # The package with the fewest candidates first, as the example
      # provider of resolvelib does.  Deps.preferred takes the demands in
      # the order it meets them, so the first plan of the two sides can
      # differ when the index has several plans (the module docstring).
      return sum(1 for _ in candidates[identifier])

    def find_matches(self, identifier, requirements, incompatibilities):
      excluded = {c.version for c in incompatibilities[identifier]}
      reqs = list(requirements[identifier])
      return [
          c for c in self.candidates.get(identifier, ())
            if c.version not in excluded
               and all(r.low <= c.version <= r.high for r in reqs)
        ]

    def is_satisfied_by(self, requirement, candidate):
      return requirement.low <= candidate.version <= requirement.high

    def get_dependencies(self, candidate):
      return candidate.requirements

  return Provider()


def resolvelib_side(index, roots):
  '''
  The resolvelib side: the plan of the resolver of pip over the same index,
  or None when it reports that no plan exists.
  '''
  start = time.perf_counter()
  import resolvelib
  from resolvelib import AbstractProvider, BaseReporter, Resolver
  from resolvelib.resolvers import ResolutionImpossible
  setup = time.perf_counter() - start
  start = time.perf_counter()
  provider = make_provider(index, AbstractProvider)
  resolver = Resolver(provider, BaseReporter())
  try:
    result = resolver.resolve(
        [_Requirement(n, lo, hi) for n, (lo, hi) in roots]
      , max_rounds=MAX_ROUNDS
      )
    plan = {name: c.version for name, c in result.mapping.items()}
  except ResolutionImpossible:
    plan = None
  solve = time.perf_counter() - start
  report = {
      'setup': setup, 'solve': solve
    , 'resolvelib': getattr(resolvelib, '__version__', None)
    }
  return plan, report


def main(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  if len(argv) != 3 or argv[0] not in ('sprite', 'resolvelib') \
      or argv[2] not in ('solvable', 'unsolvable'):
    sys.exit('usage: dependency.py sprite|resolvelib SIZE solvable|unsolvable')
  side, size, case = argv[0], int(argv[1]), argv[2]
  index, roots = depindex.make_index(size, unsolvable=(case == 'unsolvable'))
  report = {
      'side': side, 'size': size, 'case': case, 'entries': len(index)
    , 'requirements': sum(len(reqs) for _, _, reqs in index)
    , 'python': sys.version.split()[0]
    }
  if side == 'resolvelib':
    try:
      import resolvelib  # noqa: F401
    except ImportError:
      report['error'] = 'resolvelib is not importable by this Python'
      print(json.dumps(report))
      return MISSING_STATUS
    plan, fields = resolvelib_side(index, roots)
  else:
    plan, fields = sprite(index, roots)
  report.update(fields)
  report['found'] = plan is not None
  if plan is None:
    report['plan'] = None
    report['closure'] = 0
  else:
    report['plan'] = depindex.digest(index, plan, roots)
    report['closure'] = len(depindex.closure(index, plan, roots))
  print(json.dumps(report))
  return 0


if __name__ == '__main__':
  sys.exit(main())
