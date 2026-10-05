'''
The typed boundary between Python and Curry.

This package holds the type information Sprite reads from the FlatCurry
interfaces that the Curry front end writes, and the engine that types goals
and Python-built expressions with it (epic #48).  :mod:`.sigtable` is the
signature table: the type scheme of every loaded symbol, read on demand.  The
table of an interpreter is ``interp.sigtable``; a symbol exposes its scheme
as ``symbol.scheme`` and in Curry syntax as ``symbol.signature``.
:mod:`.defaulting` is the table of the PAKCS REPL, :mod:`.goals` the goals
of ``curry.eval`` and the text route.  :mod:`.engine` types one Python-built
expression: unification over the schemes (:mod:`.unify`, :mod:`.terms`),
context reduction and dictionary resolution (:mod:`.instances`), the
``exprtype`` parser (:mod:`.exprtype`) and the error catalogue
(:mod:`.errors`).  :mod:`.builder` is the typed ``curry.expr`` over the
engine, :mod:`.serialize` prints a description as Curry text.  The names
of the engine are imported on first use.
'''

from .sigtable import (
    Instance, Interface, InterfaceError, Predicate, Scheme, SignatureTable
  , find_interface, interface_candidates, show_predicate, show_scheme
  , show_type
  )

__all__ = [
    'Instance', 'Interface', 'InterfaceError', 'Predicate', 'Scheme'
  , 'SignatureTable', 'find_interface', 'interface_candidates'
  , 'show_predicate', 'show_scheme', 'show_type'
  # The engine, imported on first use.
  , 'App', 'DictTerm', 'Free', 'Iter', 'Known', 'List', 'Lit', 'Problem'
  , 'Tuple', 'Typed', 'TypeCheckError', 'build', 'describe', 'infer'
  , 'materialize', 'parse_type', 'serialize', 'spec_of'
  ]

_ENGINE_NAMES = {
    'App': 'engine', 'Free': 'engine', 'Iter': 'engine', 'Known': 'engine'
  , 'List': 'engine', 'Lit': 'engine', 'Problem': 'engine', 'Tuple': 'engine'
  , 'Typed': 'engine', 'build': 'engine', 'describe': 'engine'
  , 'infer': 'engine', 'materialize': 'engine', 'spec_of': 'engine'
  , 'DictTerm': 'instances', 'TypeCheckError': 'errors'
  , 'parse_type': 'exprtype', 'serialize': 'serialize'
  }

def __getattr__(name):
  modulename = _ENGINE_NAMES.get(name)
  if modulename is None:
    raise AttributeError('module %r has no attribute %r' % (__name__, name))
  import importlib
  module = importlib.import_module('.' + modulename, __name__)
  return getattr(module, name)
