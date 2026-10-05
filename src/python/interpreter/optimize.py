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

__all__ = ['inline_aliases', 'optimize', 'saturate_applies']

# Each optimizer is called once per function of the module, as
# optimizer(interp, ifun, imodule), in this order.  inline_aliases runs last.
# The monadic analysis then sees the call graph as the front end wrote it.
# saturate_applies runs before inline_aliases: a chain it collapses into a
# saturated call of an alias is then a call of the target.
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
  , ('%s.opt.saturate_applies'
        , lambda interp, ifun, imodule: saturate_applies(interp, ifun, imodule)
        )
  , ('%s.opt.inline_aliases'
        , lambda interp, ifun, imodule: inline_aliases(interp, ifun, imodule)
        )
  ]

# The function that applies a function value to one argument.
APPLY = analysis.APPLY

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

def saturate_applies(interp, ifun, imodule, modules=None):
  '''
  Collapse each ``apply`` whose head is known into the call it builds.

  A chain ``apply (apply h x) y`` costs a rewrite step and a node per
  ``apply``.  When the head ``h`` is a partial application of known arity
  (analysis.partial_head: an IFPCall or an ICPCall, or a call without
  arguments of a nullary function whose body is one, followed to a bounded
  depth), the chain becomes one saturated call (IFCall, or ICCall of a
  constructor) when the argument count fits the arity, a shorter partial
  application when arguments are still missing, and a saturated call
  followed by the remaining applies when there are too many.  The applies
  are rewritten from the inside out, one at a time (analysis.saturate), so
  the three cases fall out of one rule: an ``apply`` of a partial that
  misses one argument is the saturated call; one of a partial that misses
  more is the longer partial; and a saturated call is not a known head, so
  the applies after it stay.  A call of Prelude.$, the Prelude's alias of
  ``apply`` (analysis.is_apply), is an ``apply`` to this pass, which runs
  before inline_aliases; a user alias of ``apply`` is not, and its chain
  keeps the ``apply`` that inline_aliases makes of it.

  A variable head stays, and so does a call with arguments: the plan leaves
  those to later passes.  Only an ``apply`` whose head is written inside the
  expression changes; a head held in a variable may be shared with another
  use, and the variable stays the head (call-time choice).  The body of a
  nullary function is copied into the use site, as the step of that function
  would build it there, once per use.  The copy is rewritten as well: the
  pass may not have reached that function yet, and its body may hold a
  chain of its own (``g = k 1`` with ``k = f``).  So the result does not
  depend on the order of the functions in the module.

  The arity of the head comes from the symbol table of its module, which
  must agree with the missing count of the partial (analysis.partial_head),
  so the call has the arity of its symbol.  When a symbol of the copied body
  lives in a module that this module does not import, the module joins the
  imports, so the generated code links against it.

  Afterwards the partial application that the function unfolds to, if the
  function is nullary and its body is one, is recorded under
  analysis.UNFOLDING_KEY as ICurry-JSON.  So a module loaded from its
  compiled form, which has no bodies, still tells its nullary functions to
  the modules that import it.
  '''
  if modules is None:
    modules = interp.modules
  imports = set(imodule.imports)
  def join_imports(expr):
    def visitor(iobj, **kwds):
      if isinstance(iobj, types.ICall):
        symbol = analysis.lookup_symbol(iobj.symbolname, modules)
        modulename = None if symbol is None else symbol.modulename
        if modulename is not None and modulename != imodule.fullname \
            and modulename not in imports:
          imports.add(modulename)
          imodule.imports = imodule.imports + (modulename,)
    visit.visit(visitor, expr)
  def rewrite(expr):
    if isinstance(expr, types.ICall):
      expr.exprs = [rewrite(e) for e in expr.exprs]
      if analysis.is_apply(expr, modules):
        call = analysis.saturate(expr, modules)
        if call is not None:
          # The arguments before the last are copies: of the body of a
          # nullary function, or of a partial application written in the
          # expression.  The copy of a body may hold a chain of its own.
          call.exprs = [rewrite(e) for e in call.exprs]
          join_imports(call)
          return call
    elif isinstance(expr, types.IOr):
      expr.lhs = rewrite(expr.lhs)
      expr.rhs = rewrite(expr.rhs)
    return expr
  def visitor(iobj, **kwds):
    if isinstance(iobj, (types.IReturn, types.IVarAssign, types.INodeAssign)):
      iobj.expr = rewrite(iobj.expr)
  visit.visit(visitor, ifun.body)
  body = analysis.nullary_body(ifun)
  if body is not None:
    partial = analysis.partial_head(body, modules)
    if partial is not None:
      ifun.update_metadata(
          {analysis.UNFOLDING_KEY: analysis.unfolding_text(partial)}
        )

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
