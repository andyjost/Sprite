'''
Finds alias functions.

An alias is a function whose body is one call of another function on exactly
its own parameters, in order:

    f x y = g x y

The Prelude's instance methods for Int arithmetic and comparison are aliases
(i1 <= i2 = ltEqInt i1 i2; the +, -, and * wrappers).  A call of an alias
costs a rewrite step and a node that a direct call of the target does not.
The optimizer replaces such calls; see
curry.interpreter.optimize.inline_aliases.
'''
from .. import types

__all__ = [
    'ALIAS_KEY', 'alias_target', 'alias_target_of_body', 'lookup_function'
  , 'resolve_alias'
  ]

# The metadata key that names the direct target of an alias function.  A
# module loaded from its compiled form has no function bodies, so this key is
# how its aliases are known to the modules that import it.
ALIAS_KEY = 'all.alias_target'

def alias_target_of_body(ifun):
  '''
  The full name of the function that ``ifun`` is an alias of, read from its
  body, or None.  A function without a Curry body (built-in, external, or
  loaded from its compiled form) is never an alias by this test.
  '''
  block = getattr(ifun.body, 'block', None)
  if not isinstance(block, types.IBlock):
    return None
  if not isinstance(block.stmt, types.IReturn):
    return None
  call = block.stmt.expr
  if type(call) is not types.IFCall:
    return None
  if len(call.exprs) != ifun.arity:
    return None
  # The parameter bound to each variable: $k <- $0[i] binds parameter i.
  params = {}
  for decl in block.vardecls:
    if isinstance(decl, types.IFreeDecl):
      return None
  for assign in block.assigns:
    if not isinstance(assign, types.IVarAssign):
      return None
    rhs = assign.expr
    if not isinstance(rhs, types.IVarAccess):
      return None
    if rhs.vid != 0 or len(rhs.path) != 1 or assign.vid in params:
      return None
    params[assign.vid] = rhs.path[0]
  for i, expr in enumerate(call.exprs):
    if type(expr) is not types.IVar or params.get(expr.vid) != i:
      return None
  return call.symbolname

def alias_target(ifun):
  '''
  The full name of the function that ``ifun`` is an alias of, or None.  The
  answer comes from the metadata when it is there (a module loaded from its
  compiled form), else from the body.
  '''
  target = ifun.metadata.get(ALIAS_KEY)
  if target is None:
    target = alias_target_of_body(ifun)
  return target

def lookup_function(symbolname, modules):
  '''
  Finds the IFunction named by the full name ``symbolname`` among the loaded
  modules.  ``modules`` maps module names to Curry modules and packages, as
  Interpreter.modules does.  Returns None when the module is not loaded or
  has no such function.
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
  return obj.functions.get('.'.join(parts[i:]))

def resolve_alias(symbolname, modules, nargs):
  '''
  Follows aliases from the function named ``symbolname``, called with
  ``nargs`` arguments, to the function that does the work.  Returns the full
  name of that function: ``symbolname`` itself when it is not an alias, when
  its module is not loaded, or when the call is not saturated.  A chain stops
  before a target that is not loaded or that has another arity.  A chain that
  closes on itself (aliases of each other) leaves the call alone.
  '''
  ifun = lookup_function(symbolname, modules)
  if ifun is None or ifun.arity != nargs:
    return symbolname
  seen = [symbolname]
  while True:
    target = alias_target(ifun)
    if target is None:
      return seen[-1]
    if target in seen:
      return symbolname
    ifun = lookup_function(target, modules)
    if ifun is None or ifun.arity != nargs:
      return seen[-1]
    seen.append(target)
