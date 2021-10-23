from .. import types, visit
import sys

__all__ = ['set_monadic_metadata']

class TRUE(BaseException): pass

# def set_monadic_metadata(imodule, modules):
#   '''
#   Determines whether each ICurry function in a module is monadic.  The result
#   is stored in the 'all.monadic' metadata.
# 
#   To determine whether a function is monadic, its call graph is walked.  If
#   the function calls any monadic function, then it is determined to be monadic.
#   '''
#   # limit = sys.getrecursionlimit()
#   # try:
#   #   sys.setrecursionlimit(1<<30)
#   # for ifun in imodule.functions.values():
#   #   is_monadic(ifun, modules)
#   # finally:
#   #   sys.setrecursionlimit(limit)

def set_monadic_metadata(ifun, modules):
  '''
  Tells or determines whether an ICurry function is monadic.
  '''
  if isinstance(ifun, types.IFunction):
    if 'all.monadic' not in ifun.metadata:
      ifun.update_metadata({'all.monadic': False})
      visitor = lambda iobj, **kwds: _checkmonadic(iobj, modules, **kwds)
      try:
        visit.visit(visitor, ifun.body)
      except TRUE:
        result = True
      else:
        result = False
      ifun.update_metadata({'all.monadic': result})
    return ifun.metadata['all.monadic']
  else:
    return False

def _lookupfunction(symbolname, modules):
  # interp.symbol cannot be used because analysis must occur before the symbols
  # are created.  For example, we need to determine whether something like
  # Prelude.putStr is monadic before creating its symbol (which would have
  # set_monadic_metadata=True set).  interp.symbol cannot, of course, be used
  # before the symbol tables are generated.
  obj = modules
  parts = iter(symbolname.split('.'))
  while not isinstance(obj, types.IModule):
    part = next(parts)
    obj = obj[part]
    obj = getattr(obj, '.icurry', obj)
  return obj.functions.get('.'.join(parts), None)

def _checkmonadic(iobj, modules, **kwds):
  if isinstance(iobj, types.ICall):
    ifun = _lookupfunction(iobj.symbolname, modules)
    if ifun is not None:
      if set_monadic_metadata(ifun, modules):
        raise TRUE()
