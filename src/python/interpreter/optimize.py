'''
The ICurry optimizer.

The passes run when a module is loaded, before its symbols are materialized
(interpreter.import_.load): after the ICurry was read, and before either
backend generates code.  A module loaded from its compiled form carries the
keys of the passes that ran on it in its metadata and is not optimized again.
'''
from ..icurry import analysis, types, visit
from .. import common, inspect, utility
import sys

__all__ = ['inline_aliases', 'optimize']

# Each optimizer is called once per function of the module, as
# optimizer(interp, ifun, imodule), in this order.  inline_aliases runs last.
# The monadic analysis then sees the call graph as the front end wrote it.
default_optimizers = [
    ('%s.opt.set_monadic_metadata'
        , lambda interp, ifun, imodule:
              analysis.set_monadic_metadata(ifun, interp.modules)
        )
  , ('%s.opt.set_operator_metadata'
        , lambda interp, ifun, imodule: set_operator_metadata(ifun)
        )
  , ('%s.opt.replace_static_strings'
        , lambda interp, ifun, imodule: replace_static_strings(ifun)
        )
  , ('%s.opt.inline_aliases'
        , lambda interp, ifun, imodule: inline_aliases(interp, ifun, imodule)
        )
  ]

def optimize(interp, imodule, optimizers=default_optimizers):
  with utility.maxrecursion():
    for optstem, optimizer in optimizers:
      optkey = optstem % interp.backend.backend_name
      if not imodule.metadata.get(optkey, False):
        for ifun in imodule.functions.values():
          optimizer(interp, ifun, imodule)
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

def inline_aliases(interp, ifun, imodule):
  '''
  Replace each call of an alias function by a call of its target.

  An alias is a function whose body is one call of another function on
  exactly its own parameters, in order (analysis.alias_target_of_body).  The
  replacement follows a chain of aliases to its end through the loaded
  modules (analysis.resolve_alias).  It saves one rewrite step and one node
  per call.  Only a saturated call (IFCall) changes.  A partial application
  keeps the alias as its head.  The alias function itself stays: it is still
  reachable by name, as a partial application, and from modules compiled
  before this pass ran.

  The arguments of a call do not change, so the target has the arity of the
  alias.  The target may be private to its module: both backends resolve a
  symbol through the symbol table of its module, and the C++ backend exports
  every info table.  The target may be external: a call of it is the call of
  the built-in that the alias would have made.  When the target lives in a
  module that this module does not import, the module joins the imports, so
  the generated code links against it.

  Afterwards the direct target of the function, if the function is an alias,
  is recorded under analysis.ALIAS_KEY.  So a module loaded from its compiled
  form still tells its aliases to the modules that import it.
  '''
  modules = interp.modules
  imports = set(imodule.imports)
  def visitor(iobj, **kwds):
    if type(iobj) is types.IFCall:
      target = analysis.resolve_alias(
          iobj.symbolname, modules, len(iobj.exprs)
        )
      if target != iobj.symbolname:
        iobj.symbolname = target
        modulename = analysis.lookup_function(target, modules).modulename
        if modulename != imodule.fullname and modulename not in imports:
          imports.add(modulename)
          imodule.imports = imodule.imports + (modulename,)
  visit.visit(visitor, ifun.body)
  target = analysis.alias_target_of_body(ifun)
  if target is not None:
    ifun.update_metadata({analysis.ALIAS_KEY: target})
