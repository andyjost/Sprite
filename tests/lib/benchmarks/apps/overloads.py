'''
The child program of the overloads item of the applications suite.

Usage: python overloads.py SIDE [N]

SIDE is ``sprite`` or ``python``; N is the number of distinct calls (1000
by default).  The workload is one overload set of eight candidates with two
parameters each, over the class hierarchy Derived : Base, and N distinct
calls: the ordered pairs of a pool of 32 argument types (the arithmetic
types, std::nullptr_t, pointers with and without const, and top-level
const), in a fixed shuffled order.  The Sprite side asks
``Overloads.resultLine`` of example 21 (examples/21-cxx-types-overloads)
for every call.  It builds the overload set and the hierarchy once, before
the clock starts, as the driver of the example builds a set once for
several calls; the terms of the two arguments of a call are built from
Python data inside the measured time.  The Python side runs
cxxoverload.py, a plain-Python implementation of the same ranking, over
the same constant overload set.  The measured time, ``solve``, covers the
N calls; ``per_call`` is its quotient.  The imports and the overload set
are outside it (``setup``).

Both sides print one JSON object with the counts of the outcomes (unique,
ambiguous, no viable function) and a digest of the N answers.  The Sprite
side also runs the Python implementation on the same calls, after the
clock stopped, and reports ``agree``: whether the answers of the two sides
are the same, with the first difference when they are not.
'''

import hashlib, json, os, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LIBDIR = os.path.dirname(os.path.dirname(HERE))
ROOTDIR = os.path.dirname(os.path.dirname(LIBDIR))
EXAMPLE = os.path.join(ROOTDIR, 'examples', '21-cxx-types-overloads')
CXXDIR = os.path.join(ROOTDIR, 'examples', 'cxx')
if LIBDIR not in sys.path:
  sys.path.insert(0, LIBDIR)

from benchmarks.apps import cxxoverload

DEFAULT_CALLS = 1000
SEED = 20261006

def fund(name):
  return ('fund', name)

def const(t):
  return ('const', t)

def ptr(t):
  return ('ptr', t)

def cls(name):
  return ('class', name)

INT, LONG, DOUBLE, CHAR, BOOL, VOID = (
    fund('Int'), fund('Long'), fund('Double'), fund('Char'), fund('Bool')
  , fund('Void')
  )
BASE, DERIVED = cls('Base'), cls('Derived')
HIERARCHY = [('Derived', 'Base')]
# The overload set: f with two parameters, eight candidates.
CANDIDATES = [
    ('f', [INT, INT]), ('f', [LONG, DOUBLE]), ('f', [DOUBLE, LONG])
  , ('f', [ptr(VOID), BOOL]), ('f', [ptr(BASE), INT]), ('f', [ptr(DERIVED), LONG])
  , ('f', [ptr(const(INT)), CHAR]), ('f', [BOOL, ptr(const(VOID))])
  ]
# The pool of argument types: 32 types.
POOL = [fund(name) for name in cxxoverload.SPELLING if name != 'Void'] + [
    ptr(t) for t in (
        INT, const(INT), CHAR, VOID, const(VOID), BASE, const(BASE), DERIVED
      , const(DERIVED), LONG, DOUBLE, BOOL
      )
  ] + [const(t) for t in (INT, LONG, DOUBLE, CHAR)]


def calls(n):
  '''N distinct calls: ordered pairs of the pool in a fixed shuffled order.'''
  pairs = [[a, b] for a in POOL for b in POOL]
  if n > len(pairs):
    raise ValueError('at most %d distinct calls' % len(pairs))
  random.Random(SEED).shuffle(pairs)
  return pairs[:n]


def python_side(workload):
  start = time.perf_counter()
  answers = [
      cxxoverload.resolve(HIERARCHY, CANDIDATES, args) for args in workload
    ]
  return answers, {'setup': 0.0, 'solve': time.perf_counter() - start}


def sprite_side(workload):
  start = time.perf_counter()
  import curry
  curry.path.insert(0, CXXDIR)
  curry.path.insert(0, EXAMPLE)
  from curry.lib import CxxLimits, CxxType, Overloads

  def term(t):
    '''The Curry term of a type, built with curry.expr as the driver does.'''
    if t[0] == 'fund':
      return curry.expr(CxxType.Fund, getattr(CxxLimits, t[1]))
    if t[0] == 'const':
      return curry.expr(CxxType.Const, term(t[1]))
    if t[0] == 'ptr':
      return curry.expr(CxxType.Ptr, term(t[1]))
    return curry.expr(CxxType.Class, t[1], [])

  # The overload set and the hierarchy once, before the clock starts: the
  # question is the call, not the declaration of the candidates.  A name is
  # a str; curry.eval converts it to a String by the type of the goal.
  hierarchy = [(d, b) for d, b in HIERARCHY]
  candidates = [
      (name, [term(p) for p in params]) for name, params in CANDIDATES
    ]
  setup = time.perf_counter() - start
  start = time.perf_counter()
  answers = []
  for args in workload:
    answers.append(next(curry.eval(
        Overloads.resultLine, hierarchy, candidates, [term(a) for a in args]
      , converter='topython'
      )))
  solve = time.perf_counter() - start
  reference = [
      cxxoverload.resolve(HIERARCHY, CANDIDATES, args) for args in workload
    ]
  report = {'setup': setup, 'solve': solve, 'stats': dict(curry.stats())}
  report['agree'] = answers == reference
  if not report['agree']:
    i = next(i for i, (a, b) in enumerate(zip(answers, reference)) if a != b)
    report['difference'] = {
        'call': [cxxoverload.show_cxx(t) for t in workload[i]]
      , 'sprite': answers[i], 'python': reference[i]
      }
  return answers, report


def main(argv=None):
  argv = sys.argv[1:] if argv is None else argv
  if not 1 <= len(argv) <= 2 or argv[0] not in ('sprite', 'python'):
    sys.exit('usage: overloads.py sprite|python [N]')
  side = argv[0]
  n = int(argv[1]) if len(argv) > 1 else DEFAULT_CALLS
  workload = calls(n)
  answers, fields = (sprite_side if side == 'sprite' else python_side)(workload)
  report = {'side': side, 'calls': n, 'python': sys.version.split()[0]}
  report.update(fields)
  report['per_call'] = fields['solve'] / n
  report['outcomes'] = {
      'unique': sum(1 for a in answers if a.startswith('f(')),
      'ambiguous': sum(1 for a in answers if a.startswith('ambiguous')),
      'no_viable': sum(1 for a in answers if a == 'no viable function'),
    }
  report['digest'] = hashlib.sha256('\n'.join(answers).encode()).hexdigest()[:16]
  print(json.dumps(report))
  return 0


if __name__ == '__main__':
  sys.exit(main())
