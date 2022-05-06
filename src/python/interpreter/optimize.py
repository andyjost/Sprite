from ..icurry import analysis, types, visit
from .. import common, inspect, utility
import sys

__all__ = ['optimize']

default_optimizers = [
    ('%s.opt.set_monadic_metadata'
        , lambda interp, ifun: analysis.set_monadic_metadata(ifun, interp.modules)
        )
  , ('%s.opt.set_operator_metadata'
        , lambda interp, ifun: set_operator_metadata(ifun)
        )
  , ('%s.opt.replace_static_strings'
        , lambda interp, ifun: replace_static_strings(ifun)
        )
  ]

def optimize(interp, imodule, optimizers=default_optimizers):
  with utility.maxrecursion():
    for optstem, optimizer in optimizers:
      optkey = optstem % interp.backend.backend_name
      if not imodule.metadata.get(optkey, False):
        for ifun in imodule.functions.values():
          optimizer(interp, ifun)
        imodule.update_metadata({optkey: True})

def replace_static_strings(ifun):
  '''
  Replace chains of ICCall that build a static string with IString.
  '''
  replacements = analysis.find_static_strings(ifun)
  visit.replace(ifun, replacements)

def set_operator_metadata(ifun):
  if inspect.isa_operator_name(ifun.name):
    flags = ifun.metadata.get('all.flags', 0) | common.F_OPERATOR
    ifun.update_metadata({'all.flags': flags})

