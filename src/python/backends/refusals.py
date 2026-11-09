"""Diagnostics for missing externals that Sprite refuses by design.

Only consulted after primitive lookup: a registered implementation wins.
The declarations were checked against the pinned CPM package sources.
"""
from collections import namedtuple

# Bump with cxx.compiler.FORMAT_VERSION when the table or wording changes;
# image readers reject older messages.
DIAGNOSTIC_VERSION = 2

Refusal = namedtuple('Refusal', 'kind sentence')
STRONG = Refusal('strong encapsulation',
    'its results depend on the evaluation order')
GLOBAL = Refusal('backtrackable global variables',
    'their values depend on the search order')
SOLVER = Refusal('PAKCS constraint solvers',
    'they are bound to the Prolog back end of PAKCS')

# Module entries cover their missing externals. Function maps keep modules
# with pure helpers or weak-encapsulation operations narrowly scoped.
# AllSolutions has no externals; it calls Findall. ValueSequence is pure
# Curry on the PAKCS route. Upstream rewriteAll/rewriteSome reject outside
# demands using Prolog findall; Sprite's weak Control.Search.Unsafe stays.
# CLP.FD calls CLPFD; CLPR is the package's legacy real-solver module.
REFUSED_EXTERNALS = {
    'Control.AllValues': STRONG,
    'Control.Findall': STRONG,
    'Control.SearchTree': {'someSearchTree': STRONG},
    'Control.Search.SearchTree': {'someSearchTree': STRONG},
    'Control.Search.SearchTree.Unsafe': STRONG,
    'GlobalVariable': GLOBAL,
    'CLP.FD': SOLVER,
    'CLP.R': SOLVER,
    'CLPFD': SOLVER,
    'CLPR': SOLVER,
    'CLPB': SOLVER,
}


def refusal_message(fullname):
  module, _, function = fullname.rpartition('.')
  refusal = REFUSED_EXTERNALS.get(module)
  if isinstance(refusal, dict):
    refusal = refusal.get(function)
  if refusal is None:
    return None
  return ('%s: not supported by Sprite: %s; %s '
          '(see https://andyjost.github.io/Sprite/Compatibility.html)' %
          (fullname, refusal.kind, refusal.sentence))


def missing_external_message(fullname, *, inspection=False):
  return refusal_message(fullname) or (
      '%s: %snot implemented (no primitive in the runtime)' %
      (fullname, 'external, ' if inspection else ''))
