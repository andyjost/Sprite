'''
Implementation of the Prelude externals.
'''
from .....common import T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from ..control import E_RESIDUAL, E_UNWIND
from .....exceptions import *
from .. import fairscheme, graph
from ..... import show as show_module, inspect
import collections
import logging
import operator as op

logger = logging.getLogger(__name__)

def constr_eq(rts, _0):
  '''Implements =:=.'''
  lhs, rhs = [fairscheme.hnf_or_free(rts, rts.variable(_0, i)) for i in (0,1)]
  if lhs.is_boxed and rhs.is_boxed:
    ltag, rtag = lhs.info.tag, rhs.info.tag
    if ltag == T_FREE:
      if rtag == T_FREE:
        if inspect.get_freevar_id(lhs.target) != inspect.get_freevar_id(rhs.target):
          yield rts.prelude._StrictConstraint.info
          yield rts.expr(True)
          yield rts.expr((lhs, rhs))
        else:
          yield rts.prelude.True
      else:
        values = [rhs.unboxed_value] if rhs.typedef in rts.builtin_types else None
        _1 = rts.variable(_0, 0)
        _1.hnf(rhs.typedef, values)
    else:
      if rtag == T_FREE:
        values = [lhs.unboxed_value] if lhs.typedef in rts.builtin_types else None
        _1 = rts.variable(_0, 1)
        _1.hnf(lhs.typedef, values)
      else:
        if ltag == rtag: # recurse when the comparison returns 0 or False.
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            def terms():
              for i in xrange(arity):
                _1 = rts.variable(lhs, i)
                _2 = rts.variable(rhs, i)
                yield graph.Node(_0.info, _1, _2)
            expr = reduce((lambda a,b: graph.Node(conj, a, b)), terms())
            yield expr.info
            for succ in expr.successors:
              yield succ
          else:
            yield rts.prelude.True
        else:
          yield rts.prelude._Failure
  elif not lhs.is_boxed and not rhs.is_boxed:
    yield rts.prelude.True if lhs.unboxed_value == rhs.unboxed_value \
                           else rts.prelude._Failure
  else:
    raise InstantiationError('=:= cannot bind to an unboxed value')

def nonstrict_eq(rts, _0):
  '''
  Implements =:<=.

  This follows "Declarative Programming with Function Patterns," Antoy and
  Hanus, LOPSTR 2005, pg. 16.
  '''
  lhs = rts.variable(_0, 0)
  rhs = rts.variable(_0, 1)
  if lhs.is_boxed and rhs.is_boxed:
    lhs = fairscheme.hnf_or_free(rts, lhs)
    if lhs.info.tag == T_FREE:
      # Bind lhs -> rhs
      yield rts.prelude._NonStrictConstraint.info
      yield rts.expr(True)
      yield rts.expr((lhs, rhs))
    else:
      assert inspect.is_data(lhs.target)
      rhs = fairscheme.hnf_or_free(rts, rhs)
      if rhs.info.tag == T_FREE:
        rhs.hnf(typedef=lhs.typedef)
      else:
        assert inspect.is_data(rhs.target)
        if lhs.info.tag == rhs.info.tag:
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(rts.prelude, '&')
            def terms():
              for i in xrange(arity):
                _1 = rts.variable(lhs, i)
                _2 = rts.variable(rhs, i)
                yield graph.Node(_0.info, _1, _2)
            expr = reduce((lambda a,b: graph.Node(conj, a, b)), terms())
            yield expr.info
            for succ in expr.successors:
              yield succ
          else:
            yield rts.prelude.True
        else:
          yield rts.prelude._Failure
  elif not lhs.is_boxed and not rhs.is_boxed:
    yield rts.prelude.True if lhs.unboxed_value == rhs.unboxed_value \
                           else rts.prelude._Failure
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
def concurrent_and(rts, _0):
  Bool = rts.type('Prelude.Bool')
  assert rts.prelude.False.info.tag == 0
  assert rts.prelude.True.info.tag == 1
  errs = [None, None]
  i = 0
  while True:
    stepnumber = rts.stepcounter.count
    try:
      _1 = rts.variable(_0, i)
      _1.hnf(typedef=Bool)
    except E_RESIDUAL as errs[i]:
      if errs[1-i] and rts.stepcounter.count == stepnumber:
        raise
    else:
      if _1.info.tag:      # True
        yield rts.prelude._Fwd
        yield _0.successors[1-i]
      else:               # False
        yield rts.prelude.False
      return
    i = 1-i

def apply(rts, _0):
  # _0 (_Partapplic #missing term) arg
  #
  # The term is a function symbol followed zero or more arguments.
  # No forward nodes or set guards may appear around the term.
  partapplic = rts.variable(_0, 0)
  partapplic.hnf()
  missing, term = partapplic.target.successors
  assert inspect.isa_unboxed_int(missing)
  assert inspect.isa_func(term) or inspect.isa_ctor(term)
  arg = _0.target.successors[1]
  assert missing >= 1
  if missing == 1:
    yield term.info
    for t in term.successors:
      yield t
    yield arg
  else:
    yield partapplic.info
    yield missing-1
    yield graph.Node(term, *(term.successors+[arg]), partial=True)

def cond(rts, _0):
  Bool = rts.type('Prelude.Bool')
  _1 = rts.variable(_0, 0)
  _1.hnf(typedef=Bool)
  if _1.info.tag:
    yield rts.prelude._Fwd
    yield _0.successors[1]
  else:
    yield rts.prelude._Failure

def failed(rts):
  return [rts.prelude._Failure]

def choice(rts, _0):
  yield rts.prelude._Choice
  yield next(rts.idfactory)
  yield _0.successors[0]
  yield _0.successors[1]

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
  # FIXME: this function may not handle set guards properly.
  num = []
  Cons = rts.prelude.Cons
  while inspect.isa(s.target, Cons):
    _1 = rts.variable(s, 0)
    c = _1.unboxed_value
    if c.isdigit():
      num.append(c)
      s = rts.variable(s, 1)
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
  # FIXME: this function may not handle set guards properly.
  num = []
  Cons = rts.prelude.Cons
  if inspect.isa(s.target, Cons):
    _1 = rts.variable(s, 0)
    c = _1.unboxed_value
    if c in '+-':
      num.append(c)
      s = rts.variable(s, 1)
  have_dot = False
  while inspect.isa(s.target, Cons):
    _1 = rts.variable(s, 0)
    c = _1.unboxed_value
    if c.isdigit():
      num.append(c)
      s = rts.variable(s, 1)
    elif c == '.' and not have_dot:
      have_dot = True
      num.append(c)
      s = rts.variable(s, 1)
    else:
      break
  yield getattr(rts.prelude, '(,)')
  yield rts.expr(float(''.join(num) if num else 'nan'))
  yield s

class ParseError(BaseException): pass

def _getchar(rts, s):
  '''
  Get and unbox the head character of a string.  Return a pair of it and the
  tail.
  '''
  # FIXME: this function may not handle set guards properly.
  if inspect.isa(s.target, rts.prelude.Cons):
    _1 = rts.variable(s, 0)
    _2 = rts.variable(s, 1)
    return _1.unboxed_value, _2
  raise ParseError()

def _parseDecChar(rts, s, digits=None):
  '''
  Parses a string of decimal digits.  Returns the corresponding character and
  string tail.
  '''
  # FIXME: this function may not handle set guards properly.
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
  # FIXME: this function may not handle set guards properly.
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
  # FIXME: this function may not handle set guards properly.
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
  # FIXME: this function may not handle set guards properly.
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
  # FIXME: this function may not handle set guards properly.
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
  io_a = rts.variable(lhs, 0)
  io_a.hnf()
  a = rts.variable(io_a, 0)
  yield rts.prelude.apply
  yield lhs.successors[1]
  yield a

def seqIO(rts, lhs):
  _1 = rts.variable(lhs, 0)
  _1.hnf()
  yield rts.prelude._Fwd
  yield lhs.successors[1]

def returnIO(rts, _0): # DEBUG: changed from boxedfunc to rawfunc
  yield rts.prelude.IO
  yield _0.successors[0]

def putChar(rts, a):
  rts.stdout.write(a.unboxed_value)
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
  filename = rts.topython(filename.target)
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
  # FIXME: this function may not handle set guards properly.
  filename, data = func.successors
  filename = rts.topython(filename)
  stream = open(filename, 'w')
  List = rts.prelude.Cons.typedef()
  Char = rts.prelude.Char.typedef()
  while True:
    _1 = rts.variable(func, 1)
    _1.hnf(typedef=List)
    tag = _1.info.tag
    if tag == 0: # Cons
      char = rts.variable(_1, 0)
      char.hnf(typedef=Char)
      stream.write(char.unboxed_value)
      func.successors[1] = _1.successors[1]
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
    _1 = rts.variable(func, 0)
    _1.hnf()
  except (IOError, MonadError) as exc:
    yield rts.prelude.apply
    yield func.successors[1]
    yield make_monad_exception(rts, exc)
  else:
    yield rts.prelude._Fwd
    yield func.successors[0]

def ioError(rts, func):
  yield rts.prelude.error
  yield graph.Node(rts.prelude.show, func.successors[0])

def show(rts, arg):
  if arg.is_boxed:
    string = show_module.show(arg.target)
  else:
    string = str(arg.target)
  if len(string) == 1:
    string = [string]
  result = rts.expr(string)
  yield rts.prelude._Fwd
  yield result

def normalize_wrapper(rts, var, force_ground):
  if not fairscheme.N(rts, var, force_ground):
    rts.unwind()
  else:
    return var

def apply_special(rts, _0, action, **kwds):
  '''Apply with a special action applied to the argument.'''
  partapplic = rts.variable(_0, 0)
  partapplic.hnf()
  term = partapplic.successors[1]
  assert inspect.isa_func(term) # not a forward node or set guard
  with rts.catch_control(nondet=rts.is_io(term)):
    _1 = rts.variable(_0, 1)
    transformed_arg = action(rts, _1, **kwds)
  yield rts.prelude.apply
  yield _0.successors[0]
  yield transformed_arg

def apply_hnf(rts, _0):
  return apply_special(rts, _0, fairscheme.hnf)

def apply_nf(rts, _0):
  return apply_special(rts, _0, normalize_wrapper, force_ground=False)

def apply_gnf(rts, _0):
  return apply_special(rts, _0, normalize_wrapper, force_ground=True)

def ensureNotFree(rts, _0):
  _1 = fairscheme.hnf_or_free(rts, rts.variable(_0, 0))
  if rts.is_void(_1.target):
    rts.suspend(_1.target)
  else:
    yield rts.prelude._Fwd
    yield _1

def _PyGenerator(rts, gen):
  '''Implements a Python generator as a Curry list.'''
  assert isinstance(gen.target, collections.Iterator)
  try:
    item = next(gen.target)
  except StopIteration:
    yield rts.prelude.Nil
  else:
    yield rts.prelude.Cons
    yield rts.expr(item)
    yield graph.Node(rts.prelude._PyGenerator, gen.target)
