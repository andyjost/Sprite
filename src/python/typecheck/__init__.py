'''
The typed boundary between Python and Curry.

This package holds the type information Sprite reads from the FlatCurry
interfaces that the Curry front end writes, and the engine that types goals
and Python-built expressions with it (epic #48).  :mod:`.sigtable` is the
signature table: the type scheme of every loaded symbol, read on demand.  The
table of an interpreter is ``interp.sigtable``; a symbol exposes its scheme
as ``symbol.scheme`` and in Curry syntax as ``symbol.signature``.
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
  ]
