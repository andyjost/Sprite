'''
Finds the partial application that the head of an ``apply`` denotes.

A chain ``apply (apply h x) y`` costs a rewrite step and a node per
``apply``.  When the head is known, the optimizer builds the call directly;
see curry.interpreter.optimize.saturate_applies.  A head is known when it is
a partial application (IFPCall, or ICPCall of a constructor), or a call
without arguments of a nullary function whose body is one such partial
application, followed through nullary functions to a bounded depth.  The
Prelude's instance methods that fall back to a class default have that
shape:

    _impl#/=#Prelude.Eq#Prelude.Int =
        _def#/=#Prelude.Eq _inst#Prelude.Eq#Prelude.Int

and so do userError (a partial application of UserError) and showChar.  A
head that is itself an ``apply`` of a known head is known too (the body of
``g = k 1`` with ``k = f``), so the answer does not depend on the order in
which the optimizer reaches the functions.  A variable head, and a call with
arguments, are not known.

A call of Prelude.$, the Prelude's alias of ``apply``, is an ``apply`` here
(is_apply): the optimizer runs before alias inlining.  A user alias of
``apply`` (app f x = f x) is not: the source wrote the indirection, and the
pass keeps it.
'''
from .. import json as icurry_json
from .. import types
from .aliases import lookup_function, resolve_alias
import copy

__all__ = [
    'APPLY', 'MAX_UNFOLDING_DEPTH', 'UNFOLDING_KEY', 'is_apply'
  , 'lookup_constructor', 'lookup_symbol', 'nullary_body', 'partial_head'
  , 'saturate', 'unfolding', 'unfolding_text'
  ]

# The function that applies a function value to one argument, and the
# Prelude's alias of it: f $ x = f x.
APPLY = 'Prelude.apply'
DOLLAR = 'Prelude.$'

PARTIALS = (types.IFPCall, types.ICPCall)

# The metadata key under which a nullary function records the partial
# application it unfolds to, as ICurry-JSON (see unfolding_text).  A module
# loaded from its compiled form has no function bodies, so this key is how
# its nullary functions are known to the modules that import it.
UNFOLDING_KEY = 'all.unfolding'

# How many nullary functions, and applies in head position, a head is
# followed through.
MAX_UNFOLDING_DEPTH = 8

def is_apply(expr, modules):
  '''
  Tells whether ``expr`` is a saturated call of ``apply``: an IFCall with two
  arguments of Prelude.apply, or of Prelude.$ while the loaded Prelude
  defines it as an alias of apply (resolve_alias).  ``modules`` maps module
  names to Curry modules and packages, as Interpreter.modules does.

  A user alias of apply (app f x = f x) is not an apply here, though
  inline_aliases turns a call of it into one afterwards: the source wrote
  the indirection, and a program may need it to hand a known function value
  to the apply of the runtime, which the optimizer would otherwise fold
  away (a let of a bare function value does not survive the front end).
  '''
  if type(expr) is not types.IFCall or len(expr.exprs) != 2:
    return False
  if expr.symbolname == APPLY:
    return True
  return expr.symbolname == DOLLAR \
      and resolve_alias(DOLLAR, modules, 2) == APPLY

def nullary_body(ifun):
  '''
  The expression that the nullary function ``ifun`` returns, when its body is
  one return statement without declarations, or None.  A function with
  parameters, a local variable, a free variable, or a case is never unfolded.
  Neither is a function without a Curry body (built-in, external, or loaded
  from its compiled form).
  '''
  if ifun.arity != 0:
    return None
  block = getattr(ifun.body, 'block', None)
  if not isinstance(block, types.IBlock):
    return None
  if block.vardecls or block.assigns:
    return None
  if not isinstance(block.stmt, types.IReturn):
    return None
  return block.stmt.expr

def lookup_constructor(symbolname, modules):
  '''
  Finds the IConstructor named by the full name ``symbolname`` among the
  loaded modules, as lookup_function finds a function.  Returns None when
  the module is not loaded or has no such constructor.
  '''
  parts = symbolname.split('.')
  obj = modules
  i = 0
  while not isinstance(obj, types.IModule):
    if i == len(parts):
      return None
    try:
      obj = obj[parts[i]]
    except (KeyError, TypeError):
      return None
    obj = getattr(obj, '.icurry', obj)
    i += 1
  name = '.'.join(parts[i:])
  for itype in obj.types.values():
    for ictor in itype.constructors:
      if ictor.name == name:
        return ictor
  return None

def lookup_symbol(symbolname, modules):
  '''The IFunction or IConstructor named by ``symbolname``, or None.'''
  found = lookup_function(symbolname, modules)
  if found is None:
    found = lookup_constructor(symbolname, modules)
  return found

def unfolding_text(partial):
  '''The ICurry-JSON text of a partial application, for the metadata.'''
  return icurry_json.dumps(partial)

def unfolding(ifun, modules, depth=MAX_UNFOLDING_DEPTH):
  '''
  The partial application that the nullary function ``ifun`` unfolds to, as
  a fresh expression, or None.  The answer comes from the metadata when it is
  there (a module loaded from its compiled form), else from the body, which
  may itself be a call of another nullary function or an ``apply`` chain
  (see partial_head).  A text in the metadata that does not read back as a
  partial application makes the function unknown; it does not stop the
  import.
  '''
  text = ifun.metadata.get(UNFOLDING_KEY)
  if text is not None:
    try:
      partial = icurry_json.loads(text)
    except (TypeError, ValueError):
      return None
    return partial if type(partial) in PARTIALS else None
  body = nullary_body(ifun)
  if body is None:
    return None
  return partial_head(body, modules, depth)

def saturate(iapply, modules, depth=MAX_UNFOLDING_DEPTH):
  '''
  The call that the ``apply`` node ``iapply`` builds when its head is known
  (partial_head), or None.  When the partial misses one argument, the call
  is the saturated call (IFCall, or ICCall of a constructor); when it misses
  more, the call is the longer partial application.  A saturated call that
  is itself an ``apply`` (``ap = apply``, then ``ap f x``) is saturated
  again, to the bound ``depth``.  The head is a fresh copy, so the call
  shares nothing with the body of a nullary function; the argument is the
  one of ``iapply``.
  '''
  head, arg = iapply.exprs
  partial = partial_head(head, modules, depth)
  if partial is None:
    return None
  exprs = list(partial.exprs) + [arg]
  if partial.missing > 1:
    return type(partial)(partial.symbolname, partial.missing - 1, exprs)
  if type(partial) is types.ICPCall:
    return types.ICCall(partial.symbolname, exprs)
  call = types.IFCall(partial.symbolname, exprs)
  if depth > 0 and is_apply(call, modules):
    again = saturate(call, modules, depth - 1)
    if again is not None:
      return again
  return call

def partial_head(expr, modules, depth=MAX_UNFOLDING_DEPTH):
  '''
  The partial application that the head expression ``expr`` denotes, as a
  fresh IFPCall or ICPCall, or None when the head is not known.

  ``expr`` is known when it is a partial application; an IFCall without
  arguments of a nullary function that unfolds to one (``unfolding``); or an
  ``apply`` whose head is known and whose call is a partial application
  (``saturate``), through at most ``depth`` nullary functions and applies.
  ``modules`` maps module names to Curry modules and packages, as
  Interpreter.modules does.  The partial must agree with the symbol table:
  the function or constructor is loaded, and its arity is the number of
  arguments plus the missing count, which is at least one.  So a call built
  from the answer has the arity of its symbol.
  '''
  if type(expr) in PARTIALS:
    partial = expr
  elif type(expr) is types.IFCall and not expr.exprs and depth > 0:
    ifun = lookup_function(expr.symbolname, modules)
    if ifun is None or ifun.arity != 0:
      return None
    partial = unfolding(ifun, modules, depth - 1)
    if partial is None:
      return None
  elif depth > 0 and is_apply(expr, modules):
    partial = saturate(expr, modules, depth - 1)
    if partial is None or type(partial) not in PARTIALS:
      return None
  else:
    return None
  if type(partial) is types.IFPCall:
    target = lookup_function(partial.symbolname, modules)
  else:
    target = lookup_constructor(partial.symbolname, modules)
  if target is None or partial.missing < 1:
    return None
  if target.arity != partial.missing + len(partial.exprs):
    return None
  return copy.deepcopy(partial)
