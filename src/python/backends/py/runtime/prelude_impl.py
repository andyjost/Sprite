'''
Implementation of the Prelude externals.
'''
from ....common import T_FAIL, T_CONSTR, T_VAR, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from .control import E_RESIDUAL, E_UNWIND
from ....exceptions import *
from .fairscheme.algorithm import N, hnf
from ..hnfmux import demux
from . import graph
from .... import inspect
import collections
import logging
import operator as op

logger = logging.getLogger(__name__)

def hnf_or_free(rts, root, index, typedef=None, guards=None):
  '''Reduce the expression to head normal form or a free variable.'''
  try:
    return hnf(rts, root, [index], typedef, guards)
  except E_RESIDUAL:
    # The argument could be a free variable or an expression containing a free
    # variable that cannot be narrowed, such as "ensureNotFree x".
    expr, guards = graph.Node.getitem_and_guards(root, index)
    if rts.is_variable(expr):
      return expr, guards
    else:
      raise

def hnf_or_free_int(rts, root, index, guards=None):
  return hnf_or_free(rts, root, index, rts.prelude.Int.info.typedef(), guards)

def narrow_integer_args(f):
  '''
  Decorate a built-in function over integers.  This will handle the arguments,
  raising E_RESIDUAL when they are not ground.
  '''
  def repl(rts, root):
    args, guards = demux(
        hnf_or_free_int(rts, root, i) for i in range(len(root))
      )
    variables = filter(rts.is_variable, args)
    if variables:
      rts.suspend(variables)
    else:
      return f(rts, *args)
  return repl

@narrow_integer_args
def eqInt(rts, lhs, rhs):
  result = op.eq(*map(rts.topython, [lhs, rhs]))
  yield rts.prelude.True if result else rts.prelude.False

@narrow_integer_args
def ltEqInt(rts, lhs, rhs):
  result = op.le(*map(rts.topython, [lhs, rhs]))
  yield rts.prelude.True if result else rts.prelude.False

@narrow_integer_args
def plusInt(rts, lhs, rhs):
  yield rts.prelude.Int
  yield op.add(*map(rts.topython, [lhs, rhs]))

@narrow_integer_args
def minusInt(rts, lhs, rhs):
  yield rts.prelude.Int
  yield op.sub(*map(rts.topython, [lhs, rhs]))

@narrow_integer_args
def timesInt(rts, lhs, rhs):
  yield rts.prelude.Int
  yield op.mul(*map(rts.topython, [lhs, rhs]))

@narrow_integer_args
def divInt(rts, lhs, rhs):
  yield rts.prelude.Int
  yield op.floordiv(*map(rts.topython, [lhs, rhs]))

@narrow_integer_args
def modInt(rts, lhs, rhs):
  yield rts.prelude.Int
  f = lambda x, y: x - y * op.floordiv(x,y)
  yield f(*map(rts.topython, [lhs, rhs]))

@narrow_integer_args
def quotInt(rts, lhs, rhs):
  yield rts.prelude.Int
  f = lambda x, y: int(op.truediv(x, y))
  yield f(*map(rts.topython, [lhs, rhs]))

@narrow_integer_args
def remInt(rts, lhs, rhs):
  yield rts.prelude.Int
  f = lambda x, y: x - y * int(op.truediv(x, y))
  yield f(*map(rts.topython, [lhs, rhs]))

def constr_eq(rts, root):
  '''Implements =:=.'''
  (lhs, rhs), guards = demux(hnf_or_free(rts, root, i) for i in (0,1))
  if inspect.is_boxed(rts, lhs) and inspect.is_boxed(rts, rhs):
    ltag, rtag = lhs.info.tag, rhs.info.tag
    if ltag == T_VAR:
      if rtag == T_VAR:
        if lhs[0] != rhs[0]:
          yield rts.prelude._StrictConstraint.info
          yield rts.expr(True)
          yield rts.expr((lhs, rhs))
        else:
          yield rts.prelude.True
      else:
        values = [rhs[0]] if rhs.info.typedef() in rts.builtin_types else None
        hnf(rts, root, [0], rhs.info.typedef(), values, guards)
    else:
      if rtag == T_VAR:
        values = [lhs[0]] if lhs.info.typedef() in rts.builtin_types else None
        hnf(rts, root, [1], lhs.info.typedef(), values, guards)
      else:
        if ltag == rtag: # recurse when the comparison returns 0 or False.
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            terms = (graph.Node(root.info, l, r) for l,r in zip(lhs, rhs))
            expr = reduce((lambda a,b: graph.Node(conj, a, b)), terms)
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
    raise InstantiationError('=:= cannot bind to an unboxed value')

def nonstrict_eq(rts, root):
  '''
  Implements =:<=.

  This follows "Declarative Programming with Function Patterns," Antoy and
  Hanus, LOPSTR 2005, pg. 16.
  '''
  lhs, rhs = root
  if inspect.is_boxed(rts, lhs) and inspect.is_boxed(rts, rhs):
    lhs, guards = hnf_or_free(rts, root, 0)
    if lhs.info.tag == T_VAR:
      # Bind lhs -> rhs
      yield rts.prelude._NonStrictConstraint.info
      yield rts.expr(True)
      yield rts.expr((lhs, rhs))
    else:
      assert lhs.info.tag >= T_CTOR
      rhs, guards = hnf_or_free(rts, root, 1, guards=guards)
      if rhs.info.tag == T_VAR:
        hnf(rts, root, [1], typedef=lhs.info.typedef(), guards=guards)
      else:
        rhs.info.tag >= T_VAR
        if lhs.info.tag == rhs.info.tag:
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            terms = (graph.Node(root.info, l, r) for l,r in zip(lhs, rhs))
            expr = reduce((lambda a,b: graph.Node(conj, a, b)), terms)
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
      e, guards = hnf(rts, root, [i], typedef=Bool)
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
  partapplic, guards = hnf(rts, lhs, [0]) # normalize "partapplic"
  arg = lhs.successors[1]
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
    yield graph.Node(term, *(term.successors+[arg]), partial=True)

def cond(rts, lhs):
  _, guards = hnf(rts, lhs, [0]) # normalize the Boolean argument.
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
  yield graph.Node.getitem(lhs, 0, skipguards=False)
  yield graph.Node.getitem(lhs, 1, skipguards=False)

def error(rts, msg):
  msg = str(rts.topython(msg))
  raise ExecutionError(msg)

def not_used(rts, _0):
  raise RuntimeError("function 'Prelude.%s' is not used by Sprite" % _0.info.name)

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

def bindIO(rts, lhs):
  io_a, guards = hnf(rts, lhs, [0])
  yield rts.prelude.apply
  yield lhs.successors[1]
  yield io_a.successors[0]

def seqIO(rts, lhs):
  _, guards = hnf(rts, lhs, [0])
  yield rts.prelude._Fwd
  yield lhs.successors[1]

def returnIO(rts, a):
  yield rts.prelude.IO
  yield a

def putChar(rts, a):
  rts.stdout.write(a.successors[0])
  yield rts.prelude.IO
  yield graph.Node(rts.prelude.Unit)

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

def writeFile(rts, func, mode='w'):
  filename, data = func
  filename = rts.topython(filename)
  stream = open(filename, 'w')
  listtype = rts.prelude.Cons.typedef()
  chartype = rts.prelude.Char.typedef()
  while True:
    listnode, _ = hnf(rts, func, [1], listtype)
    tag = graph.utility.tag_of(listnode)
    if tag == 0: # Cons
      char, tail = listnode
      char, _ = hnf(rts, func, [1,0], chartype)
      stream.write(char.successors[0])
      func.successors[1] = tail
    elif tag == 1: # Nil
      yield rts.prelude.IO
      yield graph.Node(rts.prelude.Unit)
      break
    else:
      assert False

def appendFile(rts, func):
  return writeFile(func, 'w+')

def make_monad_exception(rts, exc):
  idx = getattr(exc, 'CTOR_INDEX', 0)
  return graph.Node(
      rts.prelude.IOError.info.typedef().constructors[idx]
    , rts.expr(iter(str(exc)))
    )

def catch(rts, func):
  try:
    _, guards = hnf(rts, func, [0])
  except (IOError, MonadError) as exc:
    yield rts.prelude.apply
    yield func.successors[1]
    yield make_monad_exception(rts, exc)
  else:
    yield rts.prelude._Fwd
    yield func[0]

def ioError(rts, func):
  yield rts.prelude.error
  yield graph.Node(rts.prelude.show, func[0])

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

def normalize(rts, func, path, ground):
  if not N(rts, func, path, ground):
    rts.unwind()
  else:
    return graph.Node.getitem_and_guards(func, path)

def apply_impl(rts, root, impl, **kwds):
  partapplic, guards = hnf(rts, root, [0])
  func = partapplic.successors[1]
  with rts.catch_control(nondet=rts.is_io(func)):
    result, guards = impl(rts, root, [1], **kwds)
  if guards:
    breakpoint()
  yield rts.prelude.apply
  yield root.successors[0]
  yield result

def apply_hnf(rts, root):
  return apply_impl(rts, root, hnf)

def apply_nf(rts, root):
  return apply_impl(rts, root, normalize, ground=False)

def apply_gnf(rts, root):
  return apply_impl(rts, root, normalize, ground=True)

def ensureNotFree(rts, root):
  arg, guards = hnf_or_free(rts, root, 0)
  if rts.is_free(arg):
    rts.suspend(arg)
  else:
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
