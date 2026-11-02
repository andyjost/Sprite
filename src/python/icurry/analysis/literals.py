'''Recover literal dispatch after translation, without changing the oracle text.

The front end implements Int patterns as equality tests followed by lifted
Boolean cases.  Only those tests on one variable and literal constants are
combined.  The recovered case is rigid: equality suspends on a free argument,
where an ordinary ICurry literal case narrows it. Two branches with no
literal retain the literal-miss fall-through and the original equality graph.
The latter is used when the head-normal-form probe finds a nonliteral.
'''
import copy
from .. import types, visit
from .aliases import lookup_function, resolve_alias
from .inlining import _block_parts, _max_vid, _has_node_assign, _substitute
from .monadic import set_monadic_metadata


def literal_switches(ifun, modules, imodule=None):
  if ifun.name.startswith('_litfallback'):
    return
  block = getattr(ifun.body, 'block', None)
  if not isinstance(block, types.IBlock) or _has_node_assign(block):
    return
  nextvid = _max_vid(block) + 1

  def instantiate(branch, params, args):
    nonlocal nextvid
    sigma = {vid: args[index] for vid, index in params.items()}
    result = copy.deepcopy(branch.block)
    def declarations(obj):
      nonlocal nextvid
      if isinstance(obj, (types.IVarDecl, types.IFreeDecl)):
        old = obj.vid
        obj.vid = nextvid
        sigma[old] = types.IVar(nextvid)
        nextvid += 1
    visit.visit(declarations, result)
    def substitute(obj):
      if isinstance(obj, (types.IVarAssign, types.IReturn)):
        obj.expr = _substitute(obj.expr, sigma)
      if isinstance(obj, types.IVarAssign):
        obj.vid = sigma[obj.vid].vid
      elif isinstance(obj, types.IVarAccess):
        obj.vid = sigma.get(obj.vid, obj).vid
      elif isinstance(obj, types.ICase):
        obj.vid = sigma.get(obj.vid, obj).vid
    visit.visit(substitute, result)
    return result

  def test(expr):
    if type(expr) is not types.IFCall or len(expr.exprs) != 2:
      return None
    name = resolve_alias(expr.symbolname, modules, 2)
    kind = {'Prelude.eqInt': types.IInt, 'Prelude.eqChar': types.IChar}.get(name)
    if kind is None:
      return None
    left, right = expr.exprs
    if isinstance(left, types.ILit):
      left, right = right, left
    if (type(left) is types.IVar and isinstance(right, types.ILit)
        and isinstance(right.lit, kind)):
      return left.vid, right.lit

  def unpack(stmt):
    if not isinstance(stmt, types.IReturn) or type(stmt.expr) is not types.IFCall:
      return None
    call = stmt.expr
    callee = lookup_function(call.symbolname, modules)
    if (callee is None or callee.modulename != ifun.modulename
        or not callee.is_private or '_COMPLEXCASE' not in callee.name):
      return None
    # Use the snapshot taken before rewriting. A helper visited earlier
    # may already contain a switch in its false branch; reading that body
    # would make later callers keep a nested switch per literal.
    bodies = getattr(imodule, '_literal_bodies', {})
    body = bodies.get(callee.fullname, getattr(callee.body, 'block', None))
    if (not isinstance(body, types.IBlock) or type(body.stmt) is not types.ICaseCons
        or _has_node_assign(body)):
      return None
    parts = _block_parts(body, 0, callee.arity)
    if parts is None or parts[1] or parts[2]:
      return None
    params = parts[0]
    index = params.get(body.stmt.vid)
    if index is None or len(call.exprs) != callee.arity:
      return None
    matched = test(call.exprs[index])
    if matched is None:
      return None
    # The other arguments are references; substituting them never duplicates
    # a call or a choice.  Branch-local bindings are renamed below.
    if any(i != index and type(arg) is not types.IVar
           for i, arg in enumerate(call.exprs)):
      return None
    branches = {b.symbolname: b for b in body.stmt.branches}
    if set(branches) != {'Prelude.False', 'Prelude.True'}:
      return None
    args = list(call.exprs)
    args[index] = types.ICCall('Prelude.True', [])
    yes = instantiate(branches['Prelude.True'], params, args)
    args[index] = types.ICCall('Prelude.False', [])
    no = instantiate(branches['Prelude.False'], params, args)
    return matched, yes, no

  def rewrite(block, positions=frozenset()):
    positions = set(positions)
    for assign in block.assigns:
      rhs = assign.expr
      if ((isinstance(rhs, types.IVarAccess) and (rhs.vid == 0 or rhs.vid in positions))
          or (type(rhs) is types.IVar and rhs.vid in positions)):
        positions.add(assign.vid)
    stmt = block.stmt
    if isinstance(stmt, types.ICase):
      for branch in stmt.branches:
        rewrite(branch.block, positions)
      return
    first = unpack(stmt)
    if first is None:
      return
    (vid, lit), yes, no = first
    if vid not in positions and imodule is None:
      return
    branches = [types.ILitBranch(lit, yes)]
    seen = {lit.value}
    visited = set()
    while not no.assigns and not no.vardecls:
      following = unpack(no.stmt)
      if following is None:
        break
      (other, value), yes, rest = following
      # Do not format the fallback expression here: it may be a deeply
      # nested literal list. Only the next dispatch identifies a cycle.
      marker = (no.stmt.expr.symbolname, other, type(value), value.value)
      if marker in visited:
        break
      visited.add(marker)
      if other != vid or type(value) is not type(lit) or value.value in seen:
        break
      seen.add(value.value)
      branches.append(types.ILitBranch(value, yes))
      no = rest
    # Keep the original call, including its equality node and lifted cases.
    original = copy.deepcopy(stmt)
    original.expr._literal_fallback = True
    names = getattr(imodule, '_literal_fallbacks', {})
    def redirect(obj):
      if isinstance(obj, types.ICall) and obj.symbolname in names:
        obj.symbolname = names[obj.symbolname]
    visit.visit(redirect, original)
    branches.append(types.ILitBranch(None, no))
    branches.append(types.ILitBranch(None, types.IBlock([], [], original)))
    switch = types.ICaseLit(vid, branches, rigid=2)
    if vid not in positions:
      # A locally built node or free variable needs a successor path from
      # the redex. Lift this whole dispatch once, capturing references only.
      declared, referenced = set(), set()
      def variables(obj):
        if isinstance(obj, (types.IVarDecl, types.IFreeDecl)):
          declared.add(obj.vid)
        elif isinstance(obj, (types.IVar, types.IVarAccess, types.ICase)):
          referenced.add(obj.vid)
      visit.visit(variables, switch)
      captured = sorted(referenced - declared)
      if 0 in captured:
        return
      index = 0
      while '_litswitch%d' % index in imodule.functions:
        index += 1
      stem = '_litswitch%d' % index
      name = imodule.fullname + '.' + stem
      body = types.IFuncBody(types.IBlock(
          [types.IVarDecl(v) for v in captured],
          [types.IVarAssign(v, types.IVarAccess(0, [i]))
           for i, v in enumerate(captured)], switch))
      clone = types.IFunction(name, len(captured), types.PRIVATE,
          [captured.index(vid)], body, modulename=imodule.fullname)
      imodule.functions[stem] = clone
      set_monadic_metadata(clone, modules)
      block.stmt = types.IReturn(types.IFCall(name, [types.IVar(v) for v in captured]))
      return
    block.stmt = switch
    for branch in branches[:-2]:
      rewrite(branch.block, positions)
  rewrite(block)

  def nested(obj):
    if not isinstance(obj, (types.IReturn, types.IVarAssign)):
      return
    stack = [(obj.__dict__, 'expr')]
    while stack:
      owner, key = stack.pop()
      expr = owner[key]
      if getattr(expr, '_literal_fallback', False):
        continue
      if type(expr) is types.IFCall and imodule is not None:
        temporary = types.IBlock([], [], types.IReturn(expr))
        rewrite(temporary)
        owner[key] = expr = temporary.stmt.expr
      if isinstance(expr, types.ICall):
        # Keep the same functional-pattern boundary as the inliner.
        pattern = len(expr.exprs) - 2 if (
            type(expr) is types.IFCall and
            expr.symbolname in ('Prelude.=:<=', 'Prelude.nonstrictEq')) else -1
        stack.extend((expr.exprs, i) for i in reversed(range(len(expr.exprs)))
                     if i != pattern)
      elif isinstance(expr, types.IOr):
        stack.extend([(expr.__dict__, 'rhs'), (expr.__dict__, 'lhs')])
  visit.visit(nested, block)
