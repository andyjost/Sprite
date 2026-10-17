'''Print the source forms of terms without the runtime dictionaries.'''

from collections.abc import Iterator
from ..toolchain.flat2icurry import flatcurry as fc
from ..typecheck.serialize import curry_literal
from ..show import show_float
from . import CurryNodeInfo

ATOM, APP, NEG = 'atom', 'app', 'neg'

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
  from .terms import Term, ValueList
  if isinstance(value, Term):
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
    text = curry_literal(value, as_char=False)
    if isinstance(value, int) and value < 0:
      return text[1:-1] if text.startswith('(') else text, NEG
    return text, ATOM
  if isinstance(value, Iterator):
    return '<iterator>', ATOM
  return str(value), APP

def show(term):
  text, kind = format_(term)
  return '(%s)' % text if kind == NEG else text
