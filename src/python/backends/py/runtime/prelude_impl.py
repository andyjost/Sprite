'''
Implementation of the Prelude externals.
'''
from ....exceptions import *
from .... import inspect
from ....tags import T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
import collections
import itertools
import logging
import operator as op
import re

from .fairscheme.freevars import get_id
from .graph import Node
from .misc import E_RESIDUAL
from . import api as runtime_api

logger = logging.getLogger(__name__)

hnf = runtime_api.FairSchemeAPI.hnf()
get_generator = runtime_api.FairSchemeAPI.get_generator()

def hnf_or_free(rts, root, index):
  '''Reduce the expression to head normal form or a free variable.'''
  try:
    return hnf(rts, root, [index])
  except E_RESIDUAL:
    # The argument could be a free variable or an expression containing a free
    # variable that cannot be narrowed, such as "ensureNotFree x".
    expr = root[index]
    if inspect.isa_freevar(rts, expr):
      return expr
    else:
      raise

def algebraic_substitution(prim_func_name=None):
  def decorator(f):
    fname = 'prim_' + f.__name__ if prim_func_name is None else prim_func_name
    def replacement(rts, root):
      if(rts.algebraic_substitution):
        return f(rts, root)
      else:
        # Perform a substitution similar to the following:
        #     eqInt x y = (prim_eqInt $# x) $# y
        assert len(root)
        conj = getattr(rts.prelude, '$#')
        args = reduce(lambda l, r: Node(conj, l, r), root)
        prim_func = getattr(rts.prelude, fname)
        return itertools.chain([prim_func.info], args)
    return replacement
  return decorator

# @algebraic_substitution()
def eqInt(rts, root):
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.isa_freevar(rts, lhs) and inspect.isa_freevar(rts, rhs):
    raise E_RESIDUAL(map(get_id, [lhs, rhs]))
  elif inspect.isa_freevar(rts, lhs):
    yield rts.integer.narrowEqInt
    yield lhs
    yield rhs
  elif inspect.isa_freevar(rts, rhs):
    yield rts.integer.narrowEqInt
    yield rhs
    yield lhs
  else:
    result = op.eq(*map(rts.topython, [lhs, rhs]))
    yield rts.prelude.True if result else rts.prelude.False

# @algebraic_substitution()
def ltEqInt(rts, root):
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.isa_freevar(rts, lhs) and inspect.isa_freevar(rts, rhs):
    raise E_RESIDUAL(map(get_id, [lhs, rhs]))
  elif inspect.isa_freevar(rts, lhs):
    yield rts.integer.narrowLtEqInt
    yield lhs
    yield rhs
  elif inspect.isa_freevar(rts, rhs):
    yield rts.integer.narrowLtEqInt
    yield rhs
    yield lhs
  else:
    result = op.le(*map(rts.topython, [lhs, rhs]))
    yield rts.prelude.True if result else rts.prelude.False

# @algebraic_substitution()
def plusInt(rts, root):
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.isa_freevar(rts, lhs) and inspect.isa_freevar(rts, rhs):
    raise E_RESIDUAL(map(get_id, [lhs, rhs]))
  elif inspect.isa_freevar(rts, lhs):
    yield rts.integer.narrowPlusInt
    yield lhs
    yield rhs
  elif inspect.isa_freevar(rts, rhs):
    yield rts.integer.narrowPlusInt
    yield rhs
    yield lhs
  else:
    yield rts.prelude.Int
    yield op.add(*map(rts.topython, [lhs, rhs]))

# @algebraic_substitution()
def minusInt(rts, root):
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.isa_freevar(rts, lhs) and inspect.isa_freevar(rts, rhs):
    raise E_RESIDUAL(map(get_id, [lhs, rhs]))
  elif inspect.isa_freevar(rts, lhs):
    yield rts.integer.narrowMinusInt
    yield lhs
    yield rhs
  elif inspect.isa_freevar(rts, rhs):
    yield rts.integer.narrowMinusIntRev
    yield lhs
    yield rhs
  else:
    yield rts.prelude.Int
    yield op.sub(*map(rts.topython, [lhs, rhs]))

# @algebraic_substitution()
def timesInt(rts, root):
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.isa_freevar(rts, lhs) and inspect.isa_freevar(rts, rhs):
    raise E_RESIDUAL(map(get_id, [lhs, rhs]))
  elif inspect.isa_freevar(rts, lhs):
    yield rts.integer.narrowTimesInt
    yield lhs
    yield rhs
  elif inspect.isa_freevar(rts, rhs):
    yield rts.integer.narrowTimesInt
    yield rhs
    yield lhs
  else:
    yield rts.prelude.Int
    yield op.mul(*map(rts.topython, [lhs, rhs]))

# @algebraic_substitution()
def divInt(rts, root):
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.isa_freevar(rts, lhs) and inspect.isa_freevar(rts, rhs):
    raise E_RESIDUAL(map(get_id, [lhs, rhs]))
  elif inspect.isa_freevar(rts, lhs):
    yield rts.integer.narrowDivInt
    yield lhs
    yield rhs
  elif inspect.isa_freevar(rts, rhs):
    yield rts.integer.narrowDivIntRev
    yield lhs
    yield rhs
  else:
    yield rts.prelude.Int
    yield op.floordiv(*map(rts.topython, [lhs, rhs]))

# @algebraic_substitution()
def modInt(rts, root):
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.isa_freevar(rts, lhs) and inspect.isa_freevar(rts, rhs):
    raise E_RESIDUAL(map(get_id, [lhs, rhs]))
  elif inspect.isa_freevar(rts, lhs):
    yield rts.integer.narrowModInt
    yield lhs
    yield rhs
  elif inspect.isa_freevar(rts, rhs):
    yield rts.integer.narrowModIntRev
    yield lhs
    yield rhs
  else:
    yield rts.prelude.Int
    f = lambda x, y: x - y * op.floordiv(x,y)
    yield f(*map(rts.topython, [lhs, rhs]))

# @algebraic_substitution()
def quotInt(rts, root):
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.isa_freevar(rts, lhs) and inspect.isa_freevar(rts, rhs):
    raise E_RESIDUAL(map(get_id, [lhs, rhs]))
  elif inspect.isa_freevar(rts, lhs):
    yield rts.integer.narrowQuotInt
    yield lhs
    yield rhs
  elif inspect.isa_freevar(rts, rhs):
    yield rts.integer.narrowQuotIntRev
    yield lhs
    yield rhs
  else:
    yield rts.prelude.Int
    f = lambda x, y: int(op.truediv(x, y))
    yield f(*map(rts.topython, [lhs, rhs]))

# @algebraic_substitution()
def remInt(rts, root):
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.isa_freevar(rts, lhs) and inspect.isa_freevar(rts, rhs):
    raise E_RESIDUAL(map(get_id, [lhs, rhs]))
  elif inspect.isa_freevar(rts, lhs):
    yield rts.integer.narrowRemInt
    yield lhs
    yield rhs
  elif inspect.isa_freevar(rts, rhs):
    yield rts.integer.narrowRemIntRev
    yield lhs
    yield rhs
  else:
    yield rts.prelude.Int
    f = lambda x, y: x - y * int(op.truediv(x, y))
    yield f(*map(rts.topython, [lhs, rhs]))

def constr_eq(rts, root):
  '''Implements =:=.'''
  lhs, rhs = (hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.is_boxed(rts, lhs) and inspect.is_boxed(rts, rhs):
    ltag, rtag = lhs.info.tag, rhs.info.tag
    if ltag == T_FREE:
      if rtag == T_FREE:
        if lhs[0] != rhs[0]:
          yield rts.prelude._StrictConstraint.info
          yield rts.expr(True)
          yield rts.expr((lhs, rhs))
        else:
          yield rts.prelude.True
      else:
        # Instantiate the variable.
        assert rtag >= T_CTOR
        if rhs.info is rts.prelude.Int.info:
          if rts.algebraic_substitution:
            yield rts.integer.bindint
            yield lhs
            yield rhs
          else:
            yield rts.prelude._NonStrictConstraint.info
            yield rts.expr(True)
            yield rts.expr((lhs, rhs))
        else:
          hnf(rts, root, [0], typedef=rhs.info.typedef())
          assert False # E_CONTINUE raised
    else:
      if rtag == T_FREE:
        # Instantiate the variable.
        assert ltag >= T_CTOR
        if lhs.info is rts.prelude.Int.info:
          if rts.algebraic_substitution:
            yield rts.integer.bindint
            yield lhs
            yield rhs
          else:
            yield rts.prelude._NonStrictConstraint.info
            yield rts.expr(True)
            yield rts.expr((rhs, lhs))
        else:
          hnf(rts, root, [1], typedef=lhs.info.typedef())
          assert False # E_CONTINUE raised
      else:
        if ltag == rtag: # recurse when the comparison returns 0 or False.
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            terms = (Node(root.info, l, r) for l,r in zip(lhs, rhs))
            expr = reduce((lambda a,b: Node(conj, a, b)), terms)
            yield expr.info
            for succ in expr:
              yield succ
          else:
            yield rts.prelude.True
        else:
          yield rts.prelude._Failure
  elif not inspect.is_boxed(rts, lhs) and not inspect.is_boxed(rts, rhs):
    yield rts.prelude.True if lhs == rhs else rts.prelude._Failure
    #                               ^^^^^^^^^^ compare unboxed values
  else:
    raise InstantiationError('=:= cannot bind to an unboxed value')

def nonstrict_eq(rts, root):
  '''
  Implements =:<=.

  This follows "Declarative Programming with Function Patterns," Antoy and
  Hanus, LOPSTR 2005, pg. 16.
  '''
  lhs, rhs = root
  if inspect.is_boxed(rts, lhs) and inspect.is_boxed(rts, rhs):
    lhs = hnf_or_free(rts, root, 0)
    if lhs.info.tag == T_FREE:
      # Bind lhs -> rhs
      yield rts.prelude._NonStrictConstraint.info
      yield rts.expr(True)
      yield rts.expr((lhs, rhs))
    else:
      assert lhs.info.tag >= T_CTOR
      rhs = hnf_or_free(rts, root, 1)
      if rhs.info.tag == T_FREE:
        hnf(rts, root, [1], typedef=lhs.info.typedef())
        assert False # E_CONTINUE should be raised in prev statement
      else:
        rhs.info.tag >= T_FREE
        if lhs.info.tag == rhs.info.tag:
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            terms = (Node(root.info, l, r) for l,r in zip(lhs, rhs))
            expr = reduce((lambda a,b: Node(conj, a, b)), terms)
            yield expr.info
            for succ in expr:
              yield succ
          else:
            yield rts.prelude.True
        else:
          yield rts.prelude._Failure
  elif not inspect.is_boxed(rts, lhs) and not inspect.is_boxed(rts, rhs):
    yield rts.prelude.True if lhs == rhs else rts.prelude._Failure
    #                         ^^^^^^^^^^ compare unboxed values
  else:
    raise InstantiationError('=:<= cannot bind to an unboxed value')

def bind_io(rts, lhs):
  io_a = hnf(rts, lhs, [0])
  yield rts.prelude.apply
  yield lhs[1]
  yield io_a[0]

def seq_io(rts, lhs):
  hnf(rts, lhs, [0])
  yield rts.prelude._Fwd
  yield lhs[1]

# Prelude.& is implemented as follows:
#   Evaluate an argument and inspect its head symbol:
#     - If true, rewrite to the other argument;
#     - If false, rewrite to false;
#     - If it suspends:
#         - if the other arg has not been inspected, work on the other arg;
#         - if any step occurred, work on the other arg;
#         - otherwise, suspend;
# Use digits.curry as an example.
def concurrent_and(rts, root):
  Bool = rts.type('Prelude.Bool')
  assert rts.prelude.False.info.tag == 0
  assert rts.prelude.True.info.tag == 1
  errs = [None, None]
  i = 0
  while True:
    stepnumber = rts.stepcounter.count

    try:
      e = hnf(rts, root, [i], typedef=Bool)
    except E_RESIDUAL as errs[i]:
      if errs[1-i] and rts.stepcounter.count == stepnumber:
        raise
    else:
      if e.info.tag:      # True
        yield rts.prelude._Fwd
        yield root[1-i]
      else:               # False
        yield rts.prelude.False
      return

    i = 1-i

def apply(rts, lhs):
  hnf(rts, lhs, [0]) # normalize "partapplic"
  partapplic, arg = lhs
  missing, term = partapplic # note: "missing" is unboxed.
  assert missing >= 1
  if missing == 1:
    yield term
    for t in term.successors:
      yield t
    yield arg
  else:
    yield partapplic
    yield missing-1
    yield Node(term, *(term.successors+[arg]), partial=True)

def cond(rts, lhs):
  hnf(rts, lhs, [0]) # normalize the Boolean argument.
  if lhs[0].info is rts.prelude.True.info:
    yield rts.prelude._Fwd
    yield lhs[1]
  else:
    yield rts.prelude._Failure

def failed(rts):
  return [rts.prelude._Failure]

def choice(rts, lhs):
  yield rts.prelude._Choice
  yield next(rts.idfactory)
  yield lhs[0]
  yield lhs[1]

def error(rts, msg):
  msg = str(rts.topython(msg))
  raise RuntimeError(msg)

# The next several functions are for parsing literals.
def readNatLiteral(rts, s):
  '''
  Parse a natural number from a Curry string.  Returns a pair consisting of the
  value and the remaining string.
  '''
  num = []
  Cons = rts.prelude.Cons
  while inspect.isa(s, Cons):
    c = rts.unbox(s[0])
    if c.isdigit():
      num.append(c)
      s = s[1]
    else:
      break
  yield getattr(rts.prelude, '(,)')
  yield rts.expr(int(''.join(num)) if num else 0)
  yield s

def readFloatLiteral(rts, s):
  '''
  Parse a floating-point number from a Curry string.  Returns a pair consisting
  of the value and the remaining string.
  '''
  num = []
  Cons = rts.prelude.Cons
  if inspect.isa(s, Cons):
    c = rts.unbox(s[0])
    if c in '+-':
      num.append(c)
      s = s[1]
  have_dot = False
  while inspect.isa(s, Cons):
    c = rts.unbox(s[0])
    if c.isdigit():
      num.append(c)
      s = s[1]
    elif c == '.' and not have_dot:
      have_dot = True
      num.append(c)
      s = s[1]
    else:
      break
  yield getattr(rts.prelude, '(,)')
  yield rts.expr(float(''.join(num) if num else 'nan'))
  yield s

class ParseError(BaseException): pass

def _getchar(rts, s):
  # Get and unbox the head character of a string.  Return a pair of it and the
  # tail.
  if inspect.isa(s, rts.prelude.Cons):
    h,t = s
    return rts.unbox(h), t
  raise ParseError()

def _parseDecChar(rts, s, digits=None):
  '''
  Parses a string of decimal digits.  Returns the corresponding character and
  string tail.
  '''
  digits = digits or []
  s_prev = s
  while True:
    c, s = _getchar(rts, s_prev)
    if c.isdigit():
      digits.append(c)
    elif not digits:
      raise ParseError()
    else:
      return unichr(int(''.join(digits), 10)).encode('utf-8'), s_prev
    s_prev = s

HEXDIGITS = set('0123456789abcdef')
def _parseHexChar(rts, s, digits=None):
  '''
  Parses a string of hexadecimal digits.  Returns the corresponding character
  and string tail.
  '''
  digits = digits or []
  s_prev = s
  while True:
    c, s = _getchar(rts, s_prev)
    if c in HEXDIGITS:
      digits.append(c)
    elif not digits:
      raise ParseError()
    else:
      return unichr(int(''.join(digits), 16)).encode('utf-8'), s_prev
    s_prev = s

ESCAPE_CODES = {
    '\\':'\\'  # \\ -> \
  , '"':'"'    # \" -> "
  , "'":"'"    # \' -> '
  , 'b':'\b', 'f':'\f', 'n':'\n', 'r':'\r', 't':'\t', 'v':'\v'
  }
def _parseEscapeCode(rts, s):
  c, s = _getchar(rts, s)
  if c in ESCAPE_CODES:
    return ESCAPE_CODES[c], s
  elif c == 'x': # hex escape code
    return _parseHexChar(rts, s)
  elif c.isdigit(): # decimal escape code
    return _parseDecChar(rts, s, [c])
  else:
    raise ParseError()

def readCharLiteral(rts, s):
  '''
  Parse a character literal from a Curry string.

  The literal begins and ends with a single quote.  The body contains an ASCII
  character other than a backslash or single quote, or a backslash followed by
  one of the following:

    - Any character in "bfnrtv".
    - A single quote.
    - A backslash.
    - A natural number less than 1114112.
    - A hexadecimal integer less than 0x110000.

  Yields:
  --------
    Components of a Curry pair consisting of the parsed character and the
    string tail following the closing quote.  If no character can be parsed,
    returns char '\0' and the original string.
  '''
  s_in = s
  try:
    # First, yield the Curry symbol for a pair.
    yield getattr(rts.prelude, '(,)')

    # Get the character.
    c, s = _getchar(rts, s)
    if c != "'":
      raise ParseError()
    c, s = _getchar(rts, s)
    if c == '\\':
      c_out, s = _parseEscapeCode(rts, s)
    elif ord(c) < 256 and c != "'":
      c_out = c
    else:
      raise ParseError()

    # Eat the closing quote.
    c, s = _getchar(rts, s)
    if c != "'":
      raise ParseError()

    # Second, yield the character as a Curry Char.
    yield rts.expr(c_out)

    # Third, yield the string tail.
    yield s
  except ParseError:
    yield rts.expr('\0')
    yield s_in

def readStringLiteral(rts, s):
  '''
  Parse a string literal from a Curry string.

  The literal begins and ends with a double quote.  The body contains a string of ASCII
  characters and uses the same escape codes as for character literals.

  Yields:
  --------
    Components of a Curry pair consisting of the parsed string literal and the
    Curry string tail following the closing quote.  If no string can be parsed,
    returns and empty string and the original string.
  '''
  s_in = s
  try:
    yield getattr(rts.prelude, '(,)')
    s_out = []
    c, s = _getchar(rts, s)
    if c != '"':
      raise ParseError()
    while True:
      c, s = _getchar(rts, s)
      if c == '\\':
        c, s = _parseEscapeCode(rts, s)
        s_out.append(c)
      elif ord(c) < 256:
        if c == '"':
          yield rts.expr(''.join(s_out))
          yield s
          return
        else:
          s_out.append(c)
      else:
        raise ParseError()
  except ParseError:
    yield rts.expr("")
    yield s_in

def returnIO(rts, a):
  yield rts.prelude.IO
  yield a

def putChar(rts, a):
  rts.stdout.write(a[0])
  yield rts.prelude.IO
  yield Node(rts.prelude.Unit)

def getChar(rts):
  yield rts.prelude.Char
  yield rts.stdin.read(1)

def generateBytes(stream, chunksize=4096):
  with stream:
    while True:
      chunk = stream.read(chunksize)
      if not chunk:
        return
      for byte in chunk:
        yield byte

def readFile(rts, filename):
  filename = rts.topython(filename)
  stream = open(filename, 'r')
  try:
    import mmap
  except ImportError:
    gen = generateBytes(stream)
  else:
    gen = iter(mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ))
  yield rts.prelude._PyGenerator
  yield gen

def show(rts, arg, xform=None):
  if inspect.is_boxed(rts, arg):
    string = arg.info.show(arg, xform)
  else:
    string = str(arg)
  if len(string) == 1:
    string = [string]
  result = rts.expr(string)
  yield rts.prelude._Fwd
  yield result

def apply_hnf(rts, root):
  yield rts.prelude.apply
  yield root[0]
  yield hnf(rts, root, [1])

if runtime_api.FAIR_SCHEME_VERSION == 1:
  from .fairscheme.algo import N
  def normalize(rts, root, path, ground):
    '''Used to implement $!! and $##.'''
    try:
      hnf(rts, root, path)
    except E_RESIDUAL:
      if ground:
        raise
      else:
        return root[path]
    target, freevars = N(rts, root, path=path)
    if ground and freevars:
      raise E_RESIDUAL(freevars)
    return target
else:
  from .fairscheme.v2.algorithm import normalize

def apply_nf(rts, root):
  yield rts.prelude.apply
  yield root[0]
  yield normalize(rts, root, [1], ground=False)

def apply_gnf(rts, root):
  yield rts.prelude.apply
  yield root[0]
  yield normalize(rts, root, [1], ground=True)

def ensureNotFree(rts, root):
  arg = root[0]
  if rts.is_freevar_node(arg):
    hnf(rts, root, [0])
  yield rts.prelude._Fwd
  yield arg

def _PyGenerator(rts, gen):
  '''Implements a Python generator as a Curry list.'''
  assert isinstance(gen, collections.Iterator)
  try:
    item = next(gen)
  except StopIteration:
    yield rts.prelude.Nil
  else:
    yield rts.prelude.Cons
    yield rts.expr(item)
    yield rts.expr(gen)
