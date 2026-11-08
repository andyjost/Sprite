"""Experimental continuation matcher for linear list-segment patterns.

SPRITE_FUNPAT_CONT=1 enables this prototype in the built-in translator.
Recognize only a whole rule of the form
``free xs,x1,..,xn,ys in (xs ++ [x1,..,xn] ++ ys =:<= arg) &> rhs``.
Anonymous prefix/suffix variables are accepted too. Other patterns retain
directed matching. Every split is enumerated; fields and the suffix stay
lazy and the continuation receives actual subterms, without binding cells.

This is an experiment, not a general equivalence claim for free arguments,
encapsulated search, residual bindings or arbitrary functional patterns.
"""

import os
from . import flatcurry as fc
from .setlift import lift_type, strip_typed


def enabled():
  return os.environ.get('SPRITE_FUNPAT_CONT') == '1'


def call(name, *args):
  return fc.Comb(fc.FuncCall, name, list(args))


def cons(head, tail):
  return fc.Comb(fc.ConsCall, fc.prelude(':'), [head, tail])


NIL = fc.Comb(fc.ConsCall, fc.prelude('[]'), [])


def named(expr, name, arity):
  return isinstance(expr, fc.Comb) and expr.name == fc.prelude(name) \
      and len(expr.args) == arity


def segment(func):
  if not isinstance(func.rule, fc.Rule):
    return None
  body = strip_typed(func.rule.body)
  if not isinstance(body, fc.Free):
    return None
  guard = strip_typed(body.body)
  if not named(guard, 'cond', 2):
    return None
  match, rhs = guard.args
  if not named(match, '=:<=', 3):
    return None
  _, pattern, subject = match.args
  if not named(pattern, '++', 2):
    return None
  prefix, rest = pattern.args
  if not named(rest, '++', 2):
    return None
  middle, suffix = rest.args
  fields = []
  while named(middle, ':', 2):
    head, middle = middle.args
    if not isinstance(head, fc.Var):
      return None
    fields.append(head.index)
  if not fields or middle != NIL:
    return None
  ends = []
  for end in (prefix, suffix):
    if isinstance(end, fc.Var):
      ends.append(end.index)
    elif named(end, 'unknown', 1):
      ends.append(None)
    else:
      return None
  bound = [v for v in [ends[0]] + fields + [ends[1]] if v is not None]
  if len(set(bound)) != len(bound) or set(bound) != set(fc.free_vars(body.vars)):
    return None
  # The argument must not itself mention the locally bound pattern names.
  if not isinstance(subject, fc.Var) or subject.index not in func.rule.args:
    return None
  return ends, fields, bound, subject, rhs


def transform_prog(prog):
  functions = []
  used = {f.name for f in prog.functions}
  count = 0
  for func in prog.functions:
    found = segment(func)
    if found is None:
      functions.append(func)
      continue
    ends, fields, bound, subject, rhs = found
    names = [(prog.name, func.name[1] + '_FPCONT_' + s)
             for s in ('scan', 'yield')]
    if any(name in used for name in names):
      functions.append(func)
      continue
    used.update(names)
    scan, continuation = names
    captured = list(func.rule.args)
    fresh = max(set(fc.all_vars(func.rule.body)) | set(captured), default=0) + 1
    prefix, tail, head, rest = range(fresh, fresh + 4)
    actual_fields = list(range(fresh + 4, fresh + 4 + len(fields)))
    tails = list(range(fresh + 4 + len(fields), fresh + 4 + 2 * len(fields)))
    values = dict(zip(fields, map(fc.Var, actual_fields)))
    if ends[0] is not None:
      values[ends[0]] = fc.Var(prefix)
    if ends[1] is not None:
      values[ends[1]] = fc.Var(tails[-1])
    captures = list(map(fc.Var, captured))
    success = call(continuation, *(captures + [values[v] for v in bound]))
    inputs = [tail] + tails[:-1]
    for inp, field, suffix in reversed(list(zip(inputs, actual_fields, tails))):
      success = fc.Case(fc.Flex, fc.Var(inp), [fc.Branch(
          fc.Pattern(fc.prelude(':'), [field, suffix]), success)])
    recurse = fc.Case(fc.Flex, fc.Var(tail), [fc.Branch(
        fc.Pattern(fc.prelude(':'), [head, rest]),
        call(scan, *(captures + [call(fc.prelude('++'), fc.Var(prefix),
            cons(fc.Var(head), NIL)), fc.Var(rest)])))])
    scanargs = captured + [prefix, tail]
    contargs = captured + bound
    functions.extend([
        func.replace(rule=fc.Rule(captured, call(scan, *(captures + [NIL, subject])))),
        fc.Func(scan, len(scanargs), fc.Private, lift_type(len(scanargs)),
            fc.Rule(scanargs, fc.Or(success, recurse))),
        fc.Func(continuation, len(contargs), fc.Private, lift_type(len(contargs)),
            fc.Rule(contargs, rhs))])
    count += 1
  return prog.replace(functions=functions) if count else prog, count
