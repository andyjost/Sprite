from ..... import inspect, show as show_module
from .....exceptions import EvaluationError
import math
import operator as op

__all__ = [
    'apply_unboxed', 'divInt', 'minusInt', 'modInt', 'plusInt', 'prim_divFloat'
  , 'prim_minusFloat', 'prim_roundFloat', 'prim_truncateFloat', 'quotInt'
  , 'remInt', 'timesInt'
  ]

# The range of Int: 64 bits, as on the C++ backend.  A result outside it is
# an error, not a wider integer (issue #105), and a division by zero is an
# error, not a Python exception (issue #106).  The messages are the ones the
# C++ backend spells (cyrt/currylib/prelude/math.cpp), so the two backends
# agree.
INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1

def apply_unboxed(rts, unboxedfunc, _0):
  '''Apply an unboxed function to the successors of _0 and box the result.'''
  result_value = unboxedfunc(*_unbox(rts, _0))
  box = BOXER[type(result_value)]
  return rts.Node(*box(rts, result_value), target=_0)

def _operand(value):
  '''The text of an operand: in parentheses when it is negative.'''
  if isinstance(value, float):
    text = show_module.show_float(value)
  else:
    text = str(value)
  return '(%s)' % text if text.startswith('-') else text

def _overflow(x, op_text, y):
  raise EvaluationError(
      'integer overflow: %s %s %s' % (_operand(x), op_text, _operand(y))
    )

def _division_error(name, x, y):
  kind = 'division by zero' if y == 0 else 'integer overflow'
  raise EvaluationError('%s: %s %s %s' % (kind, name, _operand(x), _operand(y)))

def _conversion_error(name, x):
  raise EvaluationError('integer overflow: %s %s' % (name, _operand(x)))

def _fits(value):
  return INT_MIN <= value <= INT_MAX

def plusInt(x, y):
  result = x + y
  if not _fits(result):
    _overflow(x, '+', y)
  return result

def minusInt(x, y):
  result = x - y
  if not _fits(result):
    _overflow(x, '-', y)
  return result

def timesInt(x, y):
  result = x * y
  if not _fits(result):
    _overflow(x, '*', y)
  return result

# The divisions follow the Prelude: div and mod round toward minus infinity,
# quot and rem toward zero.  The one quotient that overflows is the minimum
# divided by -1; its remainder is zero.
def divInt(x, y):
  if y == 0:
    _division_error('div', x, y)
  result = x // y
  if not _fits(result):
    _division_error('div', x, y)
  return result

def modInt(x, y):
  if y == 0:
    _division_error('mod', x, y)
  return x - y * (x // y)

def quotInt(x, y):
  if y == 0:
    _division_error('quot', x, y)
  magnitude = abs(x) // abs(y)
  result = magnitude if (x < 0) == (y < 0) else -magnitude
  if not _fits(result):
    _division_error('quot', x, y)
  return result

def remInt(x, y):
  if y == 0:
    _division_error('rem', x, y)
  magnitude = abs(x) % abs(y)
  return -magnitude if x < 0 else magnitude

def prim_divFloat(x, y):
  # The division of a Float follows IEEE 754, as on the C++ backend: an
  # infinity for a nonzero dividend over zero, NaN for 0.0 / 0.0.
  try:
    return op.truediv(y, x)
  except ZeroDivisionError:
    if y == 0 or math.isnan(y):
      return math.nan
    return math.copysign(math.inf, y) * math.copysign(1.0, x)

def prim_minusFloat(x, y):
  return y - x

def prim_truncateFloat(x):
  if not math.isfinite(x):
    _conversion_error('truncate', x)
  result = math.trunc(x)
  if not _fits(result):
    _conversion_error('truncate', x)
  return result

def prim_roundFloat(x):
  # Half away from zero, as std::round of the C++ backend and PAKCS round;
  # Python's round halves to even.
  if not math.isfinite(x):
    _conversion_error('round', x)
  magnitude = math.floor(abs(x))
  if abs(x) - magnitude >= 0.5:
    magnitude += 1
  result = int(math.copysign(magnitude, x))
  if not _fits(result):
    _conversion_error('round', x)
  return result

def _unbox(rts, _0):
  # The arguments are evaluated from the left, and the step suspends at the
  # first free variable before it touches the arguments after it, as the
  # C++ backend does (currylib/defs/unboxed.def) and as PAKCS does.  A
  # generator in a later argument then does not run while the step cannot
  # complete; that run forked the configuration once per alternative, and
  # a conjunction of such steps forked their product before it suspended.
  args = []
  for i in range(len(_0.successors)):
    arg = rts.variable(_0, i).hnf_or_free()
    if inspect.isa_freevar(arg.target):
      rts.suspend(arg.target)
    args.append(arg)
  return (arg.unboxed_value for arg in args)

BOXER = {
    bool:  lambda rts, rv: [getattr(rts.prelude, 'True' if rv else 'False')]
  , float: lambda rts, rv: [rts.prelude.Float, rv]
  , int:   lambda rts, rv: [rts.prelude.Int, rv]
  , str:   lambda rts, rv: [rts.prelude.Char, rv]
  }
