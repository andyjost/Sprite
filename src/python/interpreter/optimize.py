'''
The ICurry optimizer.

The passes run when a module is loaded, before its symbols are materialized
(``interpreter.import_.load``): after the ICurry was read, and before either
backend generates code.  A module loaded from its compiled form carries the
keys of the passes that ran on it in its metadata and is not optimized again.
'''
from ..icurry import analysis, types, visit
from .. import common, inspect, utility
from ..utility.trampoline import trampoline
import sys

__all__ = ['inline_aliases', 'inline_calls', 'optimize', 'saturate_applies']

# Each optimizer is called once per function of the module, as
# optimizer(interp, ifun, imodule), in this order.  inline_aliases runs last.
# The monadic analysis then sees the call graph as the front end wrote it.
# saturate_applies runs before inline_aliases: a chain it collapses into a
# saturated call of an alias is then a call of the target.  inline_calls runs
# between them: it sees the saturated calls, saturates the chains its own
# rewrites expose, and the bodies it copies in get their aliases replaced.
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
  , ('%s.opt.inline_calls'
        , lambda interp, ifun, imodule: inline_calls(interp, ifun, imodule)
        )
  , ('%s.opt.inline_aliases'
        , lambda interp, ifun, imodule: inline_aliases(interp, ifun, imodule)
        )
  ]

# The flag that sets the budget of inline_calls, and the budget when an
# interpreter has no such flag (a fixture).
INLINE_BUDGET_FLAG = 'inline_budget'
DEFAULT_INLINE_BUDGET = 4

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
    # The walk runs on the trampoline: the nest of calls of a long literal
    # list is one path of the tree (issue #125).
    return trampoline(_rewrite(expr))
  def _rewrite(expr):
    if isinstance(expr, types.ICall):
      exprs = []
      for e in expr.exprs:
        exprs.append((yield _rewrite(e)))
      expr.exprs = exprs
      if analysis.is_apply(expr, modules):
        call = analysis.saturate(expr, modules)
        if call is not None:
          # The arguments before the last are copies: of the body of a
          # nullary function, or of a partial application written in the
          # expression.  The copy of a body may hold a chain of its own.
          exprs = []
          for e in call.exprs:
            exprs.append((yield _rewrite(e)))
          call.exprs = exprs
          join_imports(call)
          return call
    elif isinstance(expr, types.IOr):
      expr.lhs = yield _rewrite(expr.lhs)
      expr.rhs = yield _rewrite(expr.rhs)
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

def join_imports(imodule, symbolnames, modules):
  '''
  Adds to the imports of ``imodule`` the module of every symbol of
  ``symbolnames`` that is loaded and that the module does not import yet, so
  that the generated code links against it.
  '''
  imports = set(imodule.imports)
  for symbolname in sorted(symbolnames):
    symbol = analysis.lookup_symbol(symbolname, modules)
    modulename = None if symbol is None else symbol.modulename
    if modulename is not None and modulename != imodule.fullname \
        and modulename not in imports:
      imports.add(modulename)
      imodule.imports = imodule.imports + (modulename,)

def inline_calls(interp, ifun, imodule, modules=None, budget=None):
  '''
  Replace a call of a small function by its body, and a call of a
  single-case function on a known constructor by the branch.

  The rules are in analysis.inlining.  A saturated call of a non-recursive
  function whose body is an expression of at most ``budget`` nodes (the flag
  ``inline_budget``; 4 by default; 0 turns the pass off) is replaced by the
  body.  A saturated call ``g (K a b)`` of a non-recursive function whose
  body is one case on that parameter, with a branch for ``K``, is replaced by
  the body of the branch, with the fields for the pattern variables.  Every
  argument, field, or local expression that the body uses more than once is
  bound first to a fresh variable of the caller's block, so that it is built
  once (call-time choice); a variable, a literal, or a static string is
  written at every use; an expression used once is written there; one that
  is not used is dropped.  A free variable of the body is a fresh free
  variable of the caller's block.  An ``apply`` whose head the rewrites
  expose is saturated as saturate_applies does.  The result of a rewrite is
  rewritten again, so a chain of small functions resolves to its end: after
  saturation, inlining, the known-constructor rule and the alias pass,
  ``x /= y`` on Int is ``not (eqInt x y)``.  An alias function keeps its
  body, so that inline_aliases records its target as before.

  The body that replaces a call is the body of the callee as it was before
  this pass rewrote it (analysis.inline_shape), with the saturation of apply
  chains applied: the inner calls are then rewritten where the arguments are
  known.  A function with a case in its body, other than the one case of the
  second rule, is not inlined here; the plan leaves the case at a return
  position to the un-lifting pass.  A body with a recursive let is neither
  inlined nor rewritten.  The budget counts the nodes a body builds: calls,
  partial applications, constructors, choices, and literals.

  When a copied body names a symbol of a module that this module does not
  import, the module joins the imports.  Afterwards the body of the function
  is recorded under analysis.INLINE_KEY as ICurry-JSON when the function is
  public, non-recursive, and has one of the two shapes within the limit
  (analysis.RECORD_LIMIT for an expression, analysis.CASE_LIMIT for a
  branch), or when it is private and a recorded body of the module calls it
  (analysis.recorded_functions): the selector behind a class method is
  private, and the chain needs it.  So a module loaded from its compiled
  form, which has no bodies, still tells its small functions to the modules
  that import it.  Non-recursive means not on a cycle of saturated calls: a
  partial application is a value, so a dictionary and its methods are both
  inlined (analysis.inlining).
  '''
  if modules is None:
    modules = interp.modules
  if budget is None:
    budget = interp.flags.get(INLINE_BUDGET_FLAG, DEFAULT_INLINE_BUDGET)
  inliner = analysis.Inliner(modules, budget)
  if analysis.alias_target_of_body(ifun) is None:
    inliner.rewrite(ifun)
    if inliner.symbols:
      join_imports(imodule, inliner.symbols, modules)
  else:
    # An alias keeps its body: inline_aliases records its target, and a
    # caller of the alias gets the alias inlined, then the target.
    analysis.inline_shape(ifun)
  if ifun.fullname in analysis.recorded_functions(imodule, modules):
    shape = analysis.inline_shape(ifun)
    ifun.update_metadata(
        {analysis.INLINE_KEY: analysis.inline_body_text(shape.body)}
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
