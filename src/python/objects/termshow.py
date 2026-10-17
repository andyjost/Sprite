'''Print the source forms of terms without the runtime dictionaries.'''

from collections.abc import Iterator
from contextvars import ContextVar

_CONTEXT = ContextVar('term_print_context', default=None)
from ..toolchain.flat2icurry import flatcurry as fc
from ..typecheck.serialize import curry_literal
from ..show import show_float
from . import CurryNodeInfo

ATOM, APP, NEG = 'atom', 'app', 'neg'

class Context:
  '''The names of variables and shared terms in one text.'''
  def __init__(self):
    self.variables = {}
    self.lets = {}
    self.defining = set()


def _walk(root):
  from ..expressions import typed
  from .terms import Term, Var, Reference, LetForm
  seen, stack = set(), [root]
  while stack:
    value = stack.pop()
    yield value
    if isinstance(value, (Var, Reference)):
      continue
    if isinstance(value, Term):
      if id(value) in seen:
        continue
      seen.add(id(value))
      if hasattr(value, '_text'):
        stack.extend(reversed(list(value.free_vars.values())))
      else:
        stack.append(value._form)
    elif isinstance(value, LetForm):
      stack.extend(reversed([*value.bindings.values(), value.body]))
    elif isinstance(value, (list, tuple)):
      stack.extend(reversed(value))
    elif isinstance(value, typed):
      stack.append(value.value)


def _is_reducible(value):
  from .terms import Term, ValueList
  from ..common import T_CTOR
  if not isinstance(value, Term):
    return False
  if hasattr(value, '_text'):
    return True
  if value.symbol is not None:
    return value.symbol.kind == 'function'
  form = value._form
  # Applications of function results have an apply head and no symbol.
  return (isinstance(form, list) and not isinstance(form, ValueList)
      and bool(form) and isinstance(form[0], CurryNodeInfo)
      and form[0].info.tag < T_CTOR)


def _shared_reducible(root):
  from .terms import Term
  counts, order = {}, []
  for value in _walk(root):
    if isinstance(value, Term):
      key = id(value)
      if key not in counts:
        order.append(value)
      counts[key] = counts.get(key, 0) + 1
  return [value for value in order
      if counts[id(value)] > 1 and _is_reducible(value)]


def _used_names(root):
  from .terms import Var, Reference, LetForm
  names = set()
  for value in _walk(root):
    if isinstance(value, (Var, Reference)) and value.name is not None:
      names.add(value.name)
    elif isinstance(value, LetForm):
      names.update(value.bindings)
  return names


def argument(piece):
  text, kind = piece
  return text if kind == ATOM else '(%s)' % text

def operand(piece, side, fixity):
  text, kind = piece
  if kind in (ATOM, APP):
    return text
  if kind == NEG:
    return '(%s)' % text
  assoc, prec = fixity
  child_assoc, child_prec = kind
  if child_prec > prec:
    return text
  if child_prec == prec and (
      side == 'L' and assoc == child_assoc == 'infixl'
      or side == 'R' and assoc == child_assoc == 'infixr'
    ):
    return text
  return '(%s)' % text

def application(info, args):
  from .terms import Symbol
  sym = Symbol(info, info.module)
  name = sym.name
  if name.startswith('_impl#'):
    name = name.split('#')[1]
  pieces = [format_(arg) for arg in args]
  if name == '()' or name.startswith('(') and name.endswith(')') and set(name[1:-1]) == {','}:
    if len(pieces) == sym.arity:
      return '(%s)' % ','.join(p[0] for p in pieces), ATOM
  arity = sym.arity
  scheme = info.scheme
  if scheme is not None:
    t, arrows = scheme.typeexpr, 0
    while isinstance(t, fc.FuncType):
      arrows += 1
      t = t.range
    arity = max(arity, arrows)
  direct, extra = pieces[:arity], pieces[arity:]
  operator = name and not (name[0].isalnum() or name[0] == '_' or name[0] in '([')
  head = '(%s)' % name if operator else name
  if operator and len(direct) == 2:
    assoc, prec = (sym.fixity or 'infixl 9').split()
    fixity = assoc, int(prec)
    piece = ('%s %s %s' % (operand(direct[0], 'L', fixity), name,
        operand(direct[1], 'R', fixity)), fixity)
  elif direct:
    piece = ' '.join([head, *(argument(p) for p in direct)]), APP
  else:
    piece = head, ATOM
  for arg in extra:
    piece = 'apply %s %s' % (argument(piece), argument(arg)), APP
  return piece

def format_(value):
  from ..expressions import typed
  from .terms import Term, ValueList, Var, Reference, LetForm, Char, Values, IteratorSource
  ctx = _CONTEXT.get()
  if isinstance(value, Term):
    name = ctx.lets.get(id(value))
    if name is not None and id(value) not in ctx.defining:
      return name, ATOM
  if isinstance(value, Var):
    names = ctx.variables
    if value.name is not None:
      return value.name, ATOM
    if id(value) not in names:
      names[id(value)] = '_' + alpha(len(names))
    return names[id(value)], ATOM
  if isinstance(value, Reference):
    return value.name, ATOM
  if isinstance(value, LetForm):
    return 'let %s in %s' % ('; '.join('%s = %s' % (name, format_(v)[0])
        for name, v in value.bindings.items()), format_(value.body)[0]), APP
  if isinstance(value, Values):
    return 'Values [%s]' % ','.join(format_(v)[0] for v in value), APP
  if isinstance(value, Term):
    if hasattr(value, '_text'):
      return value._text, APP
    return format_(value._form)
  if isinstance(value, typed):
    if isinstance(value.value, str):
      return curry_literal(value.value, as_char=value.exprtype == 'Char'), ATOM
    return format_(value.value)
  if isinstance(value, CurryNodeInfo):
    return application(value, ())
  if isinstance(value, list) and not isinstance(value, ValueList) and value \
      and isinstance(value[0], CurryNodeInfo):
    return application(value[0], value[1:])
  if isinstance(value, list):
    return '[%s]' % ','.join(format_(v)[0] for v in value), ATOM
  if isinstance(value, tuple):
    return '(%s)' % ','.join(format_(v)[0] for v in value), ATOM
  if isinstance(value, float):
    text = show_float(value)
    return text, NEG if value < 0 else ATOM
  if isinstance(value, (bool, int, str)):
    text = curry_literal(value, as_char=isinstance(value, Char))
    if isinstance(value, int) and value < 0:
      return text[1:-1] if text.startswith('(') else text, NEG
    return text, ATOM
  if isinstance(value, (Iterator, IteratorSource)):
    return '<iterator>', ATOM
  return str(value), APP

def show(term):
  ctx = Context()
  token = _CONTEXT.set(ctx)
  try:
    shared = _shared_reducible(term)
    if shared:
      used, i = _used_names(term), 1
      for value in shared:
        while 'x%d' % i in used:
          i += 1
        ctx.lets[id(value)] = 'x%d' % i
        i += 1
    text, kind = format_(term)
    if shared:
      declarations = []
      for value in shared:
        ctx.defining.add(id(value))
        declarations.append('%s = %s' % (ctx.lets[id(value)], format_(value)[0]))
        ctx.defining.remove(id(value))
      return 'let %s in %s' % ('; '.join(declarations), text)
    return '(%s)' % text if kind == NEG else text
  finally:
    _CONTEXT.reset(token)


def alpha(n):
  chars = []
  while True:
    chars.append(chr(97 + n % 26))
    n = n // 26 - 1
    if n < 0:
      return ''.join(reversed(chars))
