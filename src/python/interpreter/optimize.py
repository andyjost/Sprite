from ..icurry import analysis, types, visit
from .. import utility
import sys

__all__ = ['optimize']

default_optimizers = [
    lambda interp, ifun: analysis.set_monadic_metadata(ifun, interp.modules)
  , lambda interp, ifun: replace_static_strings(ifun)
  ]

def optimize(interp, imodule, optimizers=default_optimizers):
  with utility.maxrecursion():
    for ifun in imodule.functions.values():
      for optimizer in optimizers:
        optimizer(interp, ifun)


def replace_static_strings(ifun):
  '''
  Replace chains of ICCall that build a static string with IString.
  '''
  replacements = analysis.find_static_strings(ifun)
  visit.replace(ifun, replacements)

