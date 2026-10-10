'''
Inlines calls of small functions, and calls of a single-case function on a
known constructor.

Two rules of the optimizer rewrite a saturated call in place (see
curry.interpreter.optimize.inline_calls):

  * A call of a non-recursive function whose body is an expression of at
    most ``budget`` nodes is replaced by the body (ExpressionBody).  The
    budget counts the nodes the body builds: calls, partial applications,
    constructors, choices, and literals; a variable is a reference and
    counts nothing.  A body may bind local variables (a ``let`` or ``where``
    that is not recursive) and declare free variables.

  * A call ``g (K a b)`` of a non-recursive function whose body is one case
    on that parameter, with a branch for ``K``, is replaced by the body of
    the branch (CaseBody).  The fields of the constructor take the places of
    the pattern variables.

The sharing rule.  Every substitution of an expression for a variable keeps
the expression built once, as the call would have built it: an argument, a
field, the whole constructor, or a local that is used more than once is
bound to a fresh variable of the caller's block (IVarDecl and IVarAssign)
before the body is substituted; one that is used once is written at its use;
one that is not used is dropped.  Call-time choice demands it: ``g (0 ? 1)``
with ``g x = (x, x)`` yields ``(0, 0)`` and ``(1, 1)``, never ``(0, 1)``.  When
a body binds two variables to one parameter or to one field, their uses count
together, since both name one argument.  A variable, a literal, and a static
string are written at every use.  A free
variable of the body becomes a fresh free variable of the caller's block: one
per inlined call, as one per call before.  A choice in the body is one choice
per call site, as one call per site.

The body that a call is replaced by is the body as the front end wrote it
(after the saturation of apply chains), not the body after this pass
rewrote it: the inner calls of the body are then rewritten in the context of
the caller, where the arguments are known.  So the dictionary chain of a
class method on a constant dictionary resolves (section 4.2 (c) of the
phase 3 plan): ``x /= y`` on Int becomes ``not (eqInt x y)``.  The body is
copied before the function is rewritten (inline_shape), and recorded under
INLINE_KEY as ICurry-JSON when it is small enough, so that a module loaded
from its compiled form, which has no bodies, still tells its small functions
to the modules that import it.

Non-recursive means not on a cycle of saturated calls within the module: a
cycle cannot cross modules, since imports are acyclic, and a body recorded by
a compiled module was found non-recursive when the module was compiled.  A
partial application is a value, not a call: the dictionary of an instance
names its methods, and a method that falls back to a class default names the
dictionary, and both are inlined, which the dictionary chain needs.  An
``apply`` that saturates such a partial is rewritten again to the depth
MAX_DEPTH and no further.  A public function records its body; a private
one records it when a recorded body of its module names it
(recorded_functions): the selector behind a class method is private, and
the chain needs it, while a lifted case function that only its parent
calls is reached through the parent's body or not at all.

A function whose body has a case is not inlined by the first rule, and a
branch whose block has a case, an exempt, or a recursive let is not inlined
by the second: a case of the body would scrutinize a node that is not a
successor of the redex.  The plan leaves the case at a return position to
the un-lifting pass (O4).  A call of a user alias of ``apply`` (``app f x =
f x``) stays, as it stays for the saturation pass: the source wrote the
indirection, and a program may need it to hand a known function value to
the apply of the runtime.
'''
from .. import json as icurry_json
from .. import types
from .aliases import lookup_function, resolve_alias
from .partials import APPLY, is_apply, saturate
from ...utility.trampoline import trampoline
import copy

__all__ = [
    'CASE_LIMIT', 'INLINE_KEY', 'MAX_DEPTH', 'RECORD_LIMIT', 'Branch'
  , 'CaseBody', 'ExpressionBody', 'Inliner', 'body_shape', 'inline_body_text'
  , 'inline_shape', 'is_recursive', 'lookup_module', 'node_count'
  , 'recordable', 'recorded_functions', 'recursive_functions'
  ]

# The metadata key under which a function records the body that a call of it
# is replaced by, as ICurry-JSON (see inline_body_text).
INLINE_KEY = 'all.inline_body'

# The largest expression body recorded in the metadata, in nodes built; the
# default budget of the pass is 4.  An importer with a larger budget reaches
# the bodies of a compiled module up to this size.
RECORD_LIMIT = 8

# The largest branch of a single-case body that is inlined or recorded, in
# nodes built.  The branch replaces a call: what it builds, the step of the
# function would have built.  The limit bounds the generated code.
CASE_LIMIT = 32

# How many times the result of a rewrite is rewritten again.  The dictionary
# chain of a class method on a constant dictionary takes about five.
MAX_DEPTH = 16

_REFERENCES = (types.IVar, types.ILit, types.IString)

# The walks over an expression are iterative, on a stack or on the
# trampoline: a literal list of thousands of elements is a nest of cons
# calls, one per element, and a walk that recursed per element ran out of
# frames under maxrecursion (issue #125; the copy of the body in
# inline_shape was the first, at about 2700 elements).

def _subexpressions(exprs):
  '''
  Every expression under ``exprs``, parents before their parts: the
  arguments of a call and the two sides of a choice, left to right.
  '''
  stack = list(reversed(exprs))
  while stack:
    expr = stack.pop()
    yield expr
    if isinstance(expr, types.ICall):
      stack.extend(reversed(expr.exprs))
    elif isinstance(expr, types.IOr):
      stack.append(expr.rhs)
      stack.append(expr.lhs)

def node_count(expr):
  '''
  The nodes that ``expr`` builds: a call, a partial application, a
  constructor, a choice, or a literal is one node plus its arguments; a
  variable is a reference and counts nothing.
  '''
  return sum(
      1 for e in _subexpressions([expr])
        if isinstance(e, (types.ICall, types.IOr, types.ILit, types.IString))
    )

def _valid_expr(expr):
  '''Whether ``expr`` is an expression the inliner can substitute into.'''
  for e in _subexpressions([expr]):
    if isinstance(e, types.IVar):
      if e.vid == 0:
        return False
    elif not isinstance(e, (types.ILit, types.IString, types.ICall, types.IOr)):
      return False
  return True

def _count_uses(exprs, counts):
  '''Adds the occurrences of each variable in ``exprs`` to ``counts``.'''
  for e in _subexpressions(exprs):
    if isinstance(e, types.IVar):
      counts[e.vid] = counts.get(e.vid, 0) + 1
  return counts

def _symbols(exprs, found):
  '''Adds the symbol names of the calls in ``exprs`` to ``found``.'''
  for e in _subexpressions(exprs):
    if isinstance(e, types.ICall):
      found.add(e.symbolname)
  return found


class ExpressionBody(object):
  '''
  A body that returns an expression: the parameters it binds (variable to
  parameter index), the locals it binds, in order (variable and expression),
  its free variables, and the result.  ``size`` counts the nodes it builds,
  ``uses`` the occurrences of each variable.
  '''
  def __init__(self, body, params, locals, frees, result):
    self.body = body
    self.params = params
    self.locals = locals
    self.frees = frees
    self.result = result
    self.size = node_count(result) + sum(node_count(e) for _, e in locals)
    self.uses = _count_uses([e for _, e in locals] + [result], {})


class Branch(object):
  '''
  A branch of a single-case body: the pattern variables it binds (variable to
  field index), its locals, its free variables, and the result.  ``size`` and
  ``uses`` include the locals of the body before the case.
  '''
  def __init__(self, symbolname, arity, fields, locals, frees, result):
    self.symbolname = symbolname
    self.arity = arity
    self.fields = fields
    self.locals = locals
    self.frees = frees
    self.result = result
    self.size = None
    self.uses = None

  def fields_at(self, index):
    '''The pattern variables bound to the field ``index``.'''
    return [vid for vid, j in self.fields.items() if j == index]


class CaseBody(object):
  '''
  A body that is one case on a parameter: the parameters it binds, the
  locals before the case, its free variables, the variable and the parameter
  index of the scrutinee, and the branches by the full name of their
  constructor.  ``size`` is the largest branch.
  '''
  def __init__(self, body, params, locals, frees, scrutinee, branches):
    self.body = body
    self.params = params
    self.locals = locals
    self.frees = frees
    self.scrutinee = scrutinee
    self.index = params[scrutinee]
    self.branches = branches
    outer = [e for _, e in locals]
    for branch in branches.values():
      inner = [e for _, e in branch.locals] + [branch.result]
      branch.size = sum(node_count(e) for e in outer + inner)
      branch.uses = _count_uses(outer + inner, {})
    self.size = max(branch.size for branch in branches.values())


def _block_parts(block, base, limit):
  '''
  Splits the declarations and assignments of ``block``: the variables bound
  to a field of ``base`` (``base[i]`` with ``i`` below ``limit``), the
  locals, and the free variables.  None when the block has another shape.
  '''
  declared = set()
  frees = []
  for decl in block.vardecls:
    if isinstance(decl, types.IFreeDecl):
      frees.append(decl.vid)
    elif isinstance(decl, types.IVarDecl):
      declared.add(decl.vid)
    else:
      return None
  bound = {}
  locals = []
  assigned = set()
  for assign in block.assigns:
    if not isinstance(assign, types.IVarAssign):
      return None
    if assign.vid not in declared or assign.vid in assigned:
      return None
    assigned.add(assign.vid)
    expr = assign.expr
    if isinstance(expr, types.IVarAccess):
      if expr.vid != base or len(expr.path) != 1:
        return None
      if not (0 <= expr.path[0] < limit):
        return None
      bound[assign.vid] = expr.path[0]
    elif _valid_expr(expr):
      locals.append((assign.vid, expr))
    else:
      return None
  if assigned != declared:
    return None
  return bound, locals, frees

def body_shape(body, arity):
  '''
  The ExpressionBody or CaseBody of the IFuncBody ``body`` of a function of
  ``arity`` parameters, or None when the body has another shape: no block
  (a built-in, an external, or a function loaded from its compiled form), a
  recursive let, a case whose branches all have a case or an exempt, a
  variable the body does not bind, or a path the inliner does not follow.
  '''
  block = getattr(body, 'block', None)
  if not isinstance(block, types.IBlock):
    return None
  parts = _block_parts(block, 0, arity)
  if parts is None:
    return None
  params, locals, frees = parts
  bound = set(params) | set(frees) | set(vid for vid, _ in locals)
  stmt = block.stmt
  if isinstance(stmt, types.IReturn):
    if not _valid_expr(stmt.expr):
      return None
    shape = ExpressionBody(body, params, locals, frees, stmt.expr)
    return shape if set(shape.uses) <= bound else None
  elif type(stmt) is types.ICaseCons:
    if stmt.vid not in params:
      return None
    outer = _count_uses([e for _, e in locals], {})
    if not set(outer) <= bound:
      return None
    branches = {}
    for ibranch in stmt.branches:
      branch = _branch_shape(ibranch, stmt.vid, bound)
      if branch is not None:
        branches[ibranch.symbolname] = branch
    if not branches:
      return None
    return CaseBody(body, params, locals, frees, stmt.vid, branches)
  return None

def _branch_shape(ibranch, scrutinee, bound):
  block = ibranch.block
  if not isinstance(block, types.IBlock):
    return None
  if not isinstance(block.stmt, types.IReturn):
    return None
  parts = _block_parts(block, scrutinee, ibranch.arity)
  if parts is None or not _valid_expr(block.stmt.expr):
    return None
  fields, locals, frees = parts
  branch = Branch(
      ibranch.symbolname, ibranch.arity, fields, locals, frees
    , block.stmt.expr
    )
  used = _count_uses([e for _, e in locals] + [branch.result], {})
  inner = bound | set(fields) | set(frees) | set(vid for vid, _ in locals)
  return branch if set(used) <= inner else None

def inline_body_text(body):
  '''The ICurry-JSON text of a function body, for the metadata.'''
  return icurry_json.dumps(body)

def inline_shape(ifun):
  '''
  The shape of the body that a call of ``ifun`` is replaced by, or None.
  The shape is built once per function, over a copy of the body as it is
  when first asked for (before the pass rewrites the function), or over the
  body the metadata records (INLINE_KEY: a module loaded from its compiled
  form has no bodies).  A text that does not read back makes the function
  unknown; it does not stop the import.
  '''
  try:
    return ifun._inline_shape
  except AttributeError:
    pass
  shape = None
  block = getattr(ifun.body, 'block', None)
  if isinstance(block, types.IBlock):
    if body_shape(ifun.body, ifun.arity) is not None:
      shape = body_shape(copy.deepcopy(ifun.body), ifun.arity)
  else:
    text = ifun.metadata.get(INLINE_KEY)
    if text is not None:
      try:
        body = icurry_json.loads(text)
      except (TypeError, ValueError):
        body = None
      if isinstance(body, types.IFuncBody):
        shape = body_shape(body, ifun.arity)
  ifun._inline_shape = shape
  return shape

def lookup_module(modulename, modules):
  '''
  Finds the IModule named ``modulename`` among the loaded modules, as
  lookup_function finds a function, or None.
  '''
  obj = modules
  for part in modulename.split('.'):
    try:
      obj = obj[part]
    except (KeyError, TypeError):
      return None
    obj = getattr(obj, '.icurry', obj)
  return obj if isinstance(obj, types.IModule) else None

def recursive_functions(imodule):
  '''
  The full names of the functions of ``imodule`` that lie on a cycle of its
  call graph, as a frozenset: a function that calls itself, or two or more
  that call each other, through saturated calls (IFCall).  A partial
  application is a value and makes no edge.  Computed once per module, from
  the bodies as they are when first asked for, and cached on the module.  A
  function without a body has no edges.
  '''
  try:
    return imodule._inline_recursive
  except AttributeError:
    pass
  prefix = imodule.fullname + '.'
  functions = imodule.functions
  edges = {}
  for ifun in functions.values():
    callees = set()
    block = getattr(ifun.body, 'block', None)
    if isinstance(block, types.IBlock):
      for symbolname in _called(block):
        if symbolname.startswith(prefix) \
            and symbolname[len(prefix):] in functions:
          callees.add(symbolname)
    edges[ifun.fullname] = callees
  recursive = frozenset(_on_cycles(edges))
  imodule._inline_recursive = recursive
  return recursive

def _called(stmt):
  '''The symbol names of the functions called (saturated) under ``stmt``.'''
  found = set()
  if isinstance(stmt, types.IBlock):
    for assign in stmt.assigns:
      if isinstance(assign, (types.IVarAssign, types.INodeAssign)):
        _function_symbols([assign.expr], found)
    found |= _called(stmt.stmt)
  elif isinstance(stmt, types.IReturn):
    _function_symbols([stmt.expr], found)
  elif isinstance(stmt, types.ICase):
    for branch in stmt.branches:
      found |= _called(branch.block)
  return found

def _function_symbols(exprs, found):
  for e in _subexpressions(exprs):
    if type(e) is types.IFCall:
      found.add(e.symbolname)

def _on_cycles(edges):
  '''
  The nodes of ``edges`` (node to its successors) that lie on a cycle: the
  members of every strongly connected component of two or more nodes, and
  every node with an edge to itself.  Tarjan's algorithm, iterative.
  '''
  index = {}
  lowlink = {}
  stack = []
  onstack = set()
  result = set()
  counter = [0]
  for root in edges:
    if root in index:
      continue
    work = [(root, iter(edges[root]))]
    index[root] = lowlink[root] = counter[0]
    counter[0] += 1
    stack.append(root)
    onstack.add(root)
    while work:
      node, successors = work[-1]
      advanced = False
      for succ in successors:
        if succ not in index:
          index[succ] = lowlink[succ] = counter[0]
          counter[0] += 1
          stack.append(succ)
          onstack.add(succ)
          work.append((succ, iter(edges[succ])))
          advanced = True
          break
        elif succ in onstack:
          lowlink[node] = min(lowlink[node], index[succ])
      if advanced:
        continue
      work.pop()
      if work:
        parent = work[-1][0]
        lowlink[parent] = min(lowlink[parent], lowlink[node])
      if lowlink[node] == index[node]:
        component = []
        while True:
          member = stack.pop()
          onstack.discard(member)
          component.append(member)
          if member == node:
            break
        if len(component) > 1:
          result.update(component)
        elif node in edges[node]:
          result.add(node)
  return result

def is_recursive(ifun, modules):
  '''
  Whether ``ifun`` lies on a cycle of the call graph of its module.  A
  function whose module is not among ``modules`` counts as recursive: the
  inliner leaves it alone.
  '''
  imodule = lookup_module(ifun.modulename, modules)
  if imodule is None:
    return True
  return ifun.fullname in recursive_functions(imodule)


def recordable(ifun, modules):
  '''
  Whether the body of ``ifun`` is one that a module records for its
  importers: it has a shape, it is not recursive, and it is within the
  limit (RECORD_LIMIT for an expression body, CASE_LIMIT for the largest
  branch of a single-case body).
  '''
  shape = inline_shape(ifun)
  if shape is None:
    return False
  limit = RECORD_LIMIT if isinstance(shape, ExpressionBody) else CASE_LIMIT
  return shape.size <= limit and not is_recursive(ifun, modules)

def recorded_functions(imodule, modules):
  '''
  The full names of the functions of ``imodule`` whose bodies the module
  records under INLINE_KEY, as a frozenset: every public function that is
  recordable, and every private function that a recorded body names, in a
  saturated call or in a partial application, so that an importer can
  follow the chain (the lambda behind ``.`` sits in a partial application
  of the body of ``.``).  Computed once per module and cached on it.
  '''
  try:
    return imodule._inline_recorded
  except AttributeError:
    pass
  prefix = imodule.fullname + '.'
  functions = imodule.functions
  recorded = set()
  work = []
  for ifun in functions.values():
    if not ifun.is_private and recordable(ifun, modules):
      recorded.add(ifun.fullname)
      work.append(ifun)
  while work:
    shape = inline_shape(work.pop())
    for symbolname in _shape_calls(shape):
      if symbolname in recorded or not symbolname.startswith(prefix):
        continue
      ifun = functions.get(symbolname[len(prefix):])
      if ifun is not None and recordable(ifun, modules):
        recorded.add(symbolname)
        work.append(ifun)
  imodule._inline_recorded = frozenset(recorded)
  return imodule._inline_recorded

def _shape_calls(shape):
  '''
  The functions that the body of ``shape`` names: in a saturated call, or
  in a partial application, which an importer may saturate and inline.
  '''
  exprs = [e for _, e in shape.locals]
  if isinstance(shape, ExpressionBody):
    exprs.append(shape.result)
  else:
    for branch in shape.branches.values():
      exprs.extend(e for _, e in branch.locals)
      exprs.append(branch.result)
  found = set()
  _named_functions(exprs, found)
  return found

def _named_functions(exprs, found):
  for e in _subexpressions(exprs):
    if isinstance(e, (types.IFCall, types.IFPCall)):
      found.add(e.symbolname)


class _Pending(object):
  '''The declarations and assignments to insert before a statement.'''
  def __init__(self):
    self.decls = []
    self.assigns = []


class Inliner(object):
  '''
  Rewrites the body of one function at a time, in place: every saturated
  call of a known function is replaced by its body under the rules of this
  module, and every apply whose head is known is saturated
  (partials.saturate), to a fixpoint bounded by ``depth``.  ``budget`` is
  the largest expression body inlined, in nodes built; 0 turns both rules
  off.  ``symbols`` collects the symbol names that the copied bodies name,
  so the caller can join the imports of the module.
  '''
  def __init__(self, modules, budget, depth=MAX_DEPTH):
    self.modules = modules
    self.budget = budget
    self.depth = depth
    self.symbols = set()
    self.count = 0
    self.nextvid = 0

  def rewrite(self, ifun):
    '''
    Rewrites the body of ``ifun``.  Returns the number of calls and applies
    replaced.  The shape of the function is taken first, so that a caller
    reached later sees the body as it was.
    '''
    inline_shape(ifun)
    block = getattr(ifun.body, 'block', None)
    if not isinstance(block, types.IBlock) or self.budget <= 0:
      return 0
    if _has_node_assign(block):
      # The patch of a recursive let names a path of a built node.
      return 0
    self.count = 0
    self.nextvid = _max_vid(block) + 1
    self.block(block)
    return self.count

  def fresh(self):
    vid = self.nextvid
    self.nextvid += 1
    return vid

  # Statements.
  def block(self, block):
    vardecls = list(block.vardecls)
    assigns = []
    for assign in block.assigns:
      if isinstance(assign, types.IVarAssign) \
          and isinstance(assign.expr, (types.ICall, types.IOr)):
        pending = _Pending()
        assign.expr = self.expr(assign.expr, pending, 0)
        vardecls.extend(pending.decls)
        assigns.extend(pending.assigns)
      assigns.append(assign)
    stmt = block.stmt
    if isinstance(stmt, types.IReturn):
      if isinstance(stmt.expr, (types.ICall, types.IOr)):
        pending = _Pending()
        stmt.expr = self.expr(stmt.expr, pending, 0)
        vardecls.extend(pending.decls)
        assigns.extend(pending.assigns)
    elif isinstance(stmt, types.ICase):
      for branch in stmt.branches:
        self.block(branch.block)
    block.vardecls = tuple(vardecls)
    block.assigns = tuple(assigns)

  # Expressions.
  def expr(self, expr, pending, depth):
    '''
    Rewrites ``expr`` from the inside out.  The result of a rule is rewritten
    again, one level deeper, until no rule applies or the depth is reached.
    The walk over the arguments runs on the trampoline; the rewrite of a
    result (``rules``) runs a walk of its own, at most ``depth`` deep.
    '''
    return trampoline(self._expr(expr, pending, depth))

  def _expr(self, expr, pending, depth):
    '''The walk of ``expr``: a generator over the nested calls and choices.'''
    if isinstance(expr, types.ICall):
      exprs = []
      for e in expr.exprs:
        exprs.append((yield self._expr(e, pending, depth)))
      expr.exprs = exprs
      if depth < self.depth:
        result = self.rules(expr, pending, depth)
        if result is not None:
          return result
    elif isinstance(expr, types.IOr):
      expr.lhs = yield self._expr(expr.lhs, pending, depth)
      expr.rhs = yield self._expr(expr.rhs, pending, depth)
    return expr

  def rules(self, expr, pending, depth):
    '''The rewrite of the call ``expr``, or None when no rule applies.'''
    if is_apply(expr, self.modules):
      call = saturate(expr, self.modules)
      if call is None:
        return None
      self.count += 1
      _symbols([call], self.symbols)
      return self.expr(call, pending, depth + 1)
    if type(expr) is not types.IFCall:
      return None
    ifun = lookup_function(expr.symbolname, self.modules)
    if ifun is None or ifun.arity != len(expr.exprs):
      return None
    if resolve_alias(expr.symbolname, self.modules, ifun.arity) == APPLY:
      # A user alias of apply stays an indirection, as it does for the
      # saturation pass (partials.is_apply): the source wrote it, and a
      # program may need it to hand a known function value to the apply of
      # the runtime.
      return None
    shape = inline_shape(ifun)
    if shape is None:
      return None
    if isinstance(shape, ExpressionBody):
      if shape.size > self.budget:
        return None
      if is_recursive(ifun, self.modules):
        return None
      self.count += 1
      return self.instantiate(shape, expr.exprs, pending, depth)
    else:
      arg = expr.exprs[shape.index]
      if type(arg) is not types.ICCall:
        return None
      branch = shape.branches.get(arg.symbolname)
      if branch is None or len(arg.exprs) != branch.arity:
        return None
      if branch.size > CASE_LIMIT:
        return None
      if is_recursive(ifun, self.modules):
        return None
      self.count += 1
      return self.instantiate_case(shape, branch, expr.exprs, pending, depth)

  def bind(self, sigma, vids, expr, uses, pending, depth, rewrite=False):
    '''
    Maps the variables ``vids`` of the body, which name one argument, to
    ``expr`` under the sharing rule: a variable, a literal, or a static
    string as it is; an expression used once as it is; one used more
    through a fresh variable of the caller's block, so that it is built
    once; one not used is dropped.  ``uses`` counts the occurrences of all
    the variables together.  A local that gets a variable is rewritten
    first (``rewrite``); an argument was rewritten already.
    '''
    if isinstance(expr, _REFERENCES) or uses <= 1:
      image = expr
    else:
      if rewrite:
        expr = self.expr(expr, pending, depth + 1)
      fresh = self.fresh()
      pending.decls.append(types.IVarDecl(fresh))
      pending.assigns.append(types.IVarAssign(fresh, expr))
      image = types.IVar(fresh)
    for vid in vids:
      sigma[vid] = image

  def bind_frees(self, sigma, frees, pending):
    for vid in frees:
      fresh = self.fresh()
      pending.decls.append(types.IFreeDecl(fresh))
      sigma[vid] = types.IVar(fresh)

  def bind_locals(self, sigma, locals, uses, pending, depth):
    for vid, expr in locals:
      expr = _substitute(copy.deepcopy(expr), sigma)
      self.bind(sigma, [vid], expr, uses.get(vid, 0), pending, depth, True)

  def instantiate(self, shape, args, pending, depth):
    '''The expression body ``shape`` on the arguments ``args``.'''
    sigma = {}
    uses = shape.uses
    for index, vids in _by_index(shape.params).items():
      self.bind(
          sigma, vids, args[index], _uses_of(uses, vids), pending, depth
        )
    self.bind_frees(sigma, shape.frees, pending)
    self.bind_locals(sigma, shape.locals, uses, pending, depth)
    result = _substitute(copy.deepcopy(shape.result), sigma)
    _symbols([result] + [a.expr for a in pending.assigns], self.symbols)
    return self.expr(result, pending, depth + 1)

  def instantiate_case(self, shape, branch, args, pending, depth):
    '''
    The branch ``branch`` of the single-case body ``shape`` on the arguments
    ``args``, whose scrutinee is a constructor of the branch.
    '''
    sigma = {}
    uses = branch.uses
    ctor = args[shape.index]
    groups = _by_index(shape.params)
    for index, vids in groups.items():
      if index != shape.index:
        self.bind(
            sigma, vids, args[index], _uses_of(uses, vids), pending, depth
          )
    # The fields.  A field used more than once, or used in a branch that
    # also uses the whole constructor, is built once.  Every variable bound
    # to the parameter of the case names the whole.
    wholes = groups[shape.index]
    whole = _uses_of(uses, wholes)
    fieldexprs = []
    for index, expr in enumerate(ctor.exprs):
      fvids = branch.fields_at(index)
      count = sum(uses.get(vid, 0) for vid in fvids) + (1 if whole else 0)
      if isinstance(expr, _REFERENCES) or count <= 1:
        rep = expr
      else:
        fresh = self.fresh()
        pending.decls.append(types.IVarDecl(fresh))
        pending.assigns.append(types.IVarAssign(fresh, expr))
        rep = types.IVar(fresh)
      for vid in fvids:
        sigma[vid] = rep
      fieldexprs.append(rep)
    if whole:
      node = types.ICCall(ctor.symbolname, [_fresh_ref(e) for e in fieldexprs])
      self.bind(sigma, wholes, node, whole, pending, depth)
    self.bind_frees(sigma, shape.frees + branch.frees, pending)
    self.bind_locals(sigma, shape.locals, uses, pending, depth)
    self.bind_locals(sigma, branch.locals, uses, pending, depth)
    result = _substitute(copy.deepcopy(branch.result), sigma)
    _symbols([result] + [a.expr for a in pending.assigns], self.symbols)
    return self.expr(result, pending, depth + 1)


def _by_index(params):
  '''
  The variables bound to each parameter index, in the order of the body.  A
  body may bind two variables to one parameter.
  '''
  groups = {}
  for vid, index in params.items():
    groups.setdefault(index, []).append(vid)
  return groups

def _uses_of(uses, vids):
  '''The occurrences of the variables ``vids`` together.'''
  return sum(uses.get(vid, 0) for vid in vids)

def _fresh_ref(expr):
  '''
  A new object for a variable, a literal, or a static string, which may be
  written at several places; any other expression as it is, once.
  '''
  if isinstance(expr, types.IVar):
    return types.IVar(expr.vid)
  if isinstance(expr, _REFERENCES):
    return copy.deepcopy(expr)
  return expr

def _substitute(expr, sigma):
  '''
  Replaces each variable of ``expr`` by its image under ``sigma``, in place.
  A variable, a literal, or a string is a new object at each occurrence;
  another image is placed as it is, once (the sharing rule binds a repeated
  one first).  The walk does not enter an image.
  '''
  stack = []
  def image(e):
    if isinstance(e, types.IVar):
      found = sigma.get(e.vid)
      return e if found is None else _fresh_ref(found)
    if isinstance(e, (types.ICall, types.IOr)):
      stack.append(e)
    return e
  result = image(expr)
  while stack:
    node = stack.pop()
    if isinstance(node, types.ICall):
      node.exprs = [image(e) for e in node.exprs]
    else:
      node.lhs = image(node.lhs)
      node.rhs = image(node.rhs)
  return result

def _has_node_assign(stmt):
  if isinstance(stmt, types.IBlock):
    if any(isinstance(a, types.INodeAssign) for a in stmt.assigns):
      return True
    return _has_node_assign(stmt.stmt)
  elif isinstance(stmt, types.ICase):
    return any(_has_node_assign(b.block) for b in stmt.branches)
  return False

def _max_vid(stmt):
  '''The largest variable id used under ``stmt``; 0 when there is none.'''
  found = [0]
  def expr(e):
    for x in _subexpressions([e]):
      if isinstance(x, (types.IVar, types.IVarAccess)):
        found[0] = max(found[0], x.vid)
  def block(s):
    if isinstance(s, types.IBlock):
      for decl in s.vardecls:
        found[0] = max(found[0], decl.vid)
      for assign in s.assigns:
        found[0] = max(found[0], assign.vid)
        expr(assign.expr)
      block(s.stmt)
    elif isinstance(s, types.IReturn):
      expr(s.expr)
    elif isinstance(s, types.ICase):
      found[0] = max(found[0], s.vid)
      for b in s.branches:
        block(b.block)
  block(stmt)
  return found[0]
