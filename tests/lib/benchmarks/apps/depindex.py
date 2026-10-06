'''
Generated package indexes for the dependency item of the applications suite.

An index has the shape of example 15 (examples/15-dependency-solver): a list
of ``(name, version, requirements)`` entries, where a requirement is
``(name, (low, high))``, a range of versions with both bounds included.  The
versions of a package are listed newest first.

``make_index(size, unsolvable)`` builds the index of ``size`` packages and
the root requirement from a fixed seed, so every run of the harness and
every side of the measurement solves the same problem:

  * package 0 is the root, ``app``; the others are ``pkg001`` and so on;
  * every package has one to three versions;
  * a witness plan is drawn first, and every requirement of the solvable
    case allows the witness version of its target, so a plan exists;
  * a version requires up to three later packages, each within a range of
    versions (a lower and an upper bound) around the witness version, so
    the newest version of a package is not always acceptable and a
    newest-first search backtracks;
  * every package is required by at least one version of an earlier one,
    so every package is in the closure of the root under some plan;
  * the unsolvable case adds one conflict to the same index: every version
    of the root requires one version of a package c and any version of a
    package d, and every version of d requires another version of c.  No
    plan holds both.

``closure(index, plan, roots)`` gives the packages a plan needs: the roots
and the requirements of the chosen versions, transitively.  Both sides of
the measurement assign a version to the closure of the root, and
``digest`` prints a plan on the closure in index order, so two plans
compare as lines.  ``holds`` checks that a plan is consistent: the two
sides search in different orders and may find different plans of one
index (dependency.py), and each plan must hold.
'''

import random

__all__ = [
    'SEED', 'MAX_VERSIONS', 'make_index', 'closure', 'digest', 'holds'
  , 'parse_plan'
  ]

SEED = 20261006
MAX_VERSIONS = 3
MAX_REQUIREMENTS = 3


def _name(i):
  return 'app' if i == 0 else 'pkg%03d' % i


def make_index(size, unsolvable=False, seed=SEED):
  '''
  The index of ``size`` packages and the root requirement, as the pair
  ``(index, roots)``.  ``roots`` accepts every version of the root.
  '''
  if size < 2 or unsolvable and size < 3:
    raise ValueError(
        'an index needs at least two packages, three for the unsolvable case'
      )
  rng = random.Random(seed * 100003 + size)
  counts = [rng.randint(1, MAX_VERSIONS) for _ in range(size)]
  witness = [rng.randint(1, counts[i]) for i in range(size)]
  # requirements[i][v] is the list of requirements of version v of package i.
  requirements = [
      {v: [] for v in range(1, counts[i] + 1)} for i in range(size)
    ]

  def allowed(j):
    lo = rng.randint(1, witness[j])
    hi = rng.randint(witness[j], counts[j])
    return (lo, hi)

  def require(i, v, j):
    if all(name != _name(j) for name, _ in requirements[i][v]):
      requirements[i][v].append((_name(j), allowed(j)))

  for i in range(size - 1):
    later = list(range(i + 1, size))
    for v in range(1, counts[i] + 1):
      for j in rng.sample(later, min(len(later), rng.randint(0, MAX_REQUIREMENTS))):
        require(i, v, j)
  # Every package is required by some version of an earlier package.
  for j in range(1, size):
    if not any(
        name == _name(j)
            for i in range(j) for reqs in requirements[i].values()
            for name, _ in reqs
      ):
      i = rng.randrange(0, j)
      require(i, rng.randint(1, counts[i]), j)
  if unsolvable:
    choices = [j for j in range(1, size) if counts[j] >= 2]
    if not choices:
      counts[1] = 2
      requirements[1][2] = list(requirements[1][1])
      choices = [1]
    c = rng.choice(choices)
    d = rng.choice([j for j in range(1, size) if j != c])
    x = witness[c]
    y = rng.choice([v for v in range(1, counts[c] + 1) if v != x])
    for v in requirements[0]:
      requirements[0][v] = [
          r for r in requirements[0][v] if r[0] not in (_name(c), _name(d))
        ] + [(_name(c), (x, x)), (_name(d), (1, counts[d]))]
    for v in requirements[d]:
      requirements[d][v] = [
          r for r in requirements[d][v] if r[0] != _name(c)
        ] + [(_name(c), (y, y))]
  index = [
      (_name(i), v, list(requirements[i][v]))
          for i in range(size) for v in range(counts[i], 0, -1)
    ]
  roots = [(_name(0), (1, counts[0]))]
  return index, roots


def closure(index, plan, roots):
  '''
  The packages a plan needs, in index order: the packages of the roots and,
  transitively, the packages that the chosen versions require.  ``plan``
  maps a name to a version.
  '''
  requirements = {(name, version): reqs for name, version, reqs in index}
  needed = []
  todo = [name for name, _ in roots]
  while todo:
    name = todo.pop()
    if name in needed or name not in plan:
      continue
    needed.append(name)
    for dep, _ in requirements.get((name, plan[name]), []):
      todo.append(dep)
  order = {name: i for i, (name, _, _) in enumerate(reversed(index))}
  return sorted(needed, key=lambda name: -order[name])


def digest(index, plan, roots):
  '''
  The plan on the closure of the roots, as one line: ``app 2, pkg001 3``.
  Two sides that print the same line found the same plan.
  '''
  return ', '.join(
      '%s %d' % (name, plan[name]) for name in closure(index, plan, roots)
    )


def parse_plan(text):
  '''The dict of a plan that ``digest`` printed.'''
  return {
      name: int(version)
          for name, version in (item.split() for item in text.split(', '))
    }


def holds(index, plan, roots):
  '''
  True when ``plan``, a dict from name to version, is a consistent plan of
  the roots: every chosen version of the closure is in the index, and
  every root and every requirement of a chosen version of the closure is
  met by the version of its package in the plan.
  '''
  requirements = {(name, version): reqs for name, version, reqs in index}
  demands = list(roots)
  for name in closure(index, plan, roots):
    if (name, plan[name]) not in requirements:
      return False
    demands += requirements[name, plan[name]]
  return all(
      name in plan and lo <= plan[name] <= hi for name, (lo, hi) in demands
    )
