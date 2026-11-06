from ...common import F_MONADIC
from .. import types
from .aliases import lookup_function

__all__ = ['set_monadic_metadata']

class TRUE(BaseException): pass

def set_monadic_metadata(ifun, modules):
  '''
  Determines whether an ICurry function is monadic.

  The result is stored in the 'all.monadic' metadata and also in 'all.flags' by
  OR-ing with F_MONADIC.  This apparent redundancy is needed because
  'all.monadic' is actually a tristate: True or False indicates the monadic
  check has been performed, while its absense indicates the check needs to be
  performed.

  To determine whether a function is monadic, its call graph is walked.  If the
  function calls any monadic function outside an unsafePerformIO argument,
  then it is determined to be monadic.  The unsafe primitive runs that
  argument as an I/O action itself; its caller produces a pure value.
  '''
  if isinstance(ifun, types.IFunction):
    if 'all.monadic' not in ifun.metadata:
      flags = ifun.metadata.get('all.flags', 0)
      if flags & F_MONADIC:
        ifun.update_metadata({'all.monadic': True})
      else:
        ifun.update_metadata({'all.monadic': False})
        visitor = lambda iobj, **kwds: _checkmonadic(iobj, modules, **kwds)
        try:
          _visit_calls(visitor, ifun.body)
        except TRUE:
          ifun.update_metadata({
              'all.flags': flags | F_MONADIC
            , 'all.monadic': True
            })
          return True
    return ifun.metadata['all.monadic']
  else:
    return False

def _visit_calls(visitor, body):
  # Keep the walk iterative, as in visit.visit: literal strings may be deep.
  pending = [(body, False)]
  while pending:
    iobj, expanded = pending.pop()
    if expanded:
      visitor(iobj)
      continue
    if isinstance(iobj, types.ICall) and \
        iobj.symbolname == 'System.IO.Unsafe.unsafePerformIO':
      # Only this primitive consumes an IO action to produce a pure value.
      # Do not propagate effects from the action it owns.
      pending.extend((arg, False) for arg in reversed(iobj.exprs[1:]))
      continue
    pending.append((iobj, True))
    if isinstance(iobj, types.IBlock):
      children = (*iobj.vardecls, *iobj.assigns, iobj.stmt)
    elif isinstance(iobj, types.IObject):
      children = iobj.children
    else:
      children = ()
    pending.extend((child, False) for child in reversed(children))

def _lookupfunction(symbolname, modules):
  # interp.symbol cannot be used because analysis must occur before the symbols
  # are created.  For example, we need to determine whether something like
  # Prelude.putStr is monadic before creating its symbol (which would have
  # set_monadic_metadata=True set).  interp.symbol cannot, of course, be used
  # before the symbol tables are generated.
  return lookup_function(symbolname, modules)

def _checkmonadic(iobj, modules, **kwds):
  if isinstance(iobj, types.ICall):
    ifun = _lookupfunction(iobj.symbolname, modules)
    if ifun is not None:
      if set_monadic_metadata(ifun, modules):
        raise TRUE()
