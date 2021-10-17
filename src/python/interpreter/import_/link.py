'''
Code to convert ICurry into the API objects found in curry.objects.
'''

from ... import config, icurry
from .lazy_function import LazyFunction
from ...objects.handle import getHandle
from ...utility import visitation
import collections

__all__ = ['link']

@visitation.dispatch.on('idef')
def link(interp, idef, moduleobj, extern=None): # pragma: no cover
  '''
  Link compiled Curry into the function NodeInfo tables.
  '''
  assert False

@link.when(collections.Mapping)
def link(interp, mapping, *args, **kwds):
  for item in mapping.itervalues():
   link(interp, item, *args, **kwds)

@link.when(icurry.IModule)
def link(interp, imodule, moduleobj, extern=None):
  link(interp, imodule.functions, moduleobj, extern)

@link.when(icurry.IFunction)
def link(interp, ifun, moduleobj, extern=None):
  info = getHandle(moduleobj).getsymbol(ifun.name).info
  # Compile interactive code right away.  Otherwise, if lazycompile is set,
  # delay compilation until the function is actually used.  See InfoTable in
  # interpreter/runtime.py.
  lazyf = LazyFunction(interp, ifun, extern)
  allowed_lazy = ifun.modulename != config.interactive_modname()
  if allowed_lazy and interp.flags['lazycompile']:
    info.step = lazyf
  else:
    info.step = lazyf.materialize()

