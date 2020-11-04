'''
Implementation of the Prelude externals.
'''
from ..exceptions import *
from . import conversions
from .. import icurry
from .. import inspect
from . import runtime
from ..utility.unboxed import unboxed
import collections
import itertools
import logging
import operator
import re

logger = logging.getLogger(__name__)

def apply(interp, lhs):
  interp.hnf(lhs, [0]) # normalize "partapplic"
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
    yield runtime.Node(term, *(term.successors+[arg]), partial=True)

def cond(interp, lhs):
  interp.hnf(lhs, [0]) # normalize the Boolean argument.
  # import code
  # code.interact(local=dict(globals(), **locals()))
  if lhs[0].info is interp.prelude.True.info:
    yield interp.prelude._Fwd
    yield lhs[1]
  else:
    yield interp.prelude._Failure

def failed(interp):
  return [interp.prelude._Failure]

def choice(interp, lhs):
  yield interp.prelude._Choice
  yield next(interp._idfactory_)
  yield lhs[0]
  yield lhs[1]

def error(interp, msg):
  msg = str(interp.topython(msg))
  raise RuntimeError(msg)

def _try_hnf(interp, root, index):
  try:
    return interp.hnf(root, [index])
  except runtime.E_RESIDUAL:
    freevar = root[index]
    assert inspect.isa_freevar(interp, freevar)
    return freevar

def eq_constr(interp, root):
  '''Implements =:=.'''
  lhs, rhs = (_try_hnf(interp, root, i) for i in (0,1))
  if inspect.is_boxed(interp, lhs) and inspect.is_boxed(interp, rhs):
    ltag, rtag = lhs.info.tag, rhs.info.tag
    if ltag == runtime.T_FREE:
      if rtag == runtime.T_FREE:
        if lhs[0] != rhs[0]:
          # Unify variables => _Binding True (x, y)
          yield interp.prelude._Binding.info
          yield interp.expr(True)
          yield interp.expr((lhs, rhs))
        else:
          yield interp.prelude.True
      else:
        # Instantiate the variable.
        assert rtag >= runtime.T_CTOR
        interp.hnf(root, [0], typedef=rhs.info.typedef())
        assert False # E_CONTINUE raised
    else:
      if rtag == runtime.T_FREE:
        # Instantiate the variable.
        assert ltag >= runtime.T_CTOR
        interp.hnf(root, [1], typedef=lhs.info.typedef())
        assert False # E_CONTINUE raised
      else:
        if ltag == rtag: # recurse when the comparison returns 0 or False.
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(interp.prelude, '&')
            terms = (runtime.Node(root.info, l, r) for l,r in zip(lhs, rhs))
            expr = reduce((lambda a,b: runtime.Node(conj, a, b)), terms)
            yield expr.info
            for succ in expr:
              yield succ
          else:
            yield interp.prelude.True
        else:
          yield interp.prelude._Failure
  elif not inspect.is_boxed(interp, lhs) and not inspect.is_boxed(interp, rhs):
    yield interp.prelude.True if lhs == rhs else interp.prelude._Failure
    #                            ^^^^^^^^^^ compare unboxed values
  else:
    raise InstantiationError('=:= cannot bind to an unboxed value')

def eq_constr_lazy(interp, root):
  '''
  Implements =:<=.

  This follows "Declarative Programming with Function Patterns," Antoy and
  Hanus, LOPSTR 2005, pg. 16.
  '''
  lhs, rhs = root
  if inspect.is_boxed(interp, lhs) and inspect.is_boxed(interp, rhs):
    lhs = _try_hnf(interp, root, 0)
    if lhs.info.tag == runtime.T_FREE:
      # Bind lhs -> rhs
      yield interp.prelude._Binding.info
      yield interp.expr(True)
      yield interp.expr((lhs, rhs))
    else:
      assert lhs.info.tag >= runtime.T_CTOR
      rhs = _try_hnf(interp, root, 1)
      if rhs.info.tag == runtime.T_FREE:
        interp.hnf(root, [1], typedef=lhs.info.typedef())
        assert False # E_CONTINUE raised
      else:
        rhs.info.tag >= runtime.T_FREE
        if lhs.info.tag == rhs.info.tag:
          arity = lhs.info.arity
          assert arity == rhs.info.arity
          if arity:
            conj = getattr(interp.prelude, '&')
            terms = (runtime.Node(root.info, l, r) for l,r in zip(lhs, rhs))
            expr = reduce((lambda a,b: runtime.Node(conj, a, b)), terms)
            yield expr.info
            for succ in expr:
              yield succ
          else:
            yield interp.prelude.True
        else:
          yield interp.prelude._Failure
  elif not inspect.is_boxed(interp, lhs) and not inspect.is_boxed(interp, rhs):
    yield interp.prelude.True if lhs == rhs else interp.prelude._Failure
    #                            ^^^^^^^^^^ compare unboxed values
  else:
    raise InstantiationError('=:<= cannot bind to an unboxed value')

def compose_io(interp, lhs):
  io_a = interp.hnf(lhs, [0])
  yield interp.prelude.apply
  yield lhs[1]
  yield conversions.unbox(interp, io_a)

# Prelude.& is implemented as follows:
#   Evaluate an argument and inspect its head symbol:
#     - If true, rewrite to the other argument;
#     - If false, rewrite to false;
#     - If it suspends:
#         - if the other arg has not been inspected, work on the other arg;
#         - if any step occurred, work on the other arg;
#         - otherwise, suspend;
# Use digits.curry as an example.
def concurrent_and(interp, root):
  Bool = interp.type('Prelude.Bool')
  assert interp.prelude.False.info.tag == 0
  assert interp.prelude.True.info.tag == 1
  errs = [None, None]
  i = 0
  while True:
    stepnumber = interp.stepcounter.count

    try:
      e = interp.hnf(root, [i], typedef=Bool)
    except runtime.E_RESIDUAL as errs[i]:
      if errs[1-i] and interp.stepcounter.count == stepnumber:
        raise
    else:
      if e.info.tag:      # True
        yield interp.prelude._Fwd
        yield root[1-i]
      else:               # False
        yield interp.prelude.False
      return

    i = 1-i

# The next several functions are for parsing literals.
def readNatLiteral(interp, s):
  '''
  Parse a natural number from a Curry string.  Returns a pair consisting of the
  value and the remaining string.
  '''
  num = []
  Cons = interp.prelude.Cons
  while inspect.isa(s, Cons):
    c = interp.unbox(s[0])
    if c.isdigit():
      num.append(c)
      s = s[1]
    else:
      break
  yield getattr(interp.prelude, '(,)')
  yield interp.expr(int(''.join(num)) if num else 0)
  yield s

def readFloatLiteral(interp, s):
  '''
  Parse a floating-point number from a Curry string.  Returns a pair consisting
  of the value and the remaining string.
  '''
  num = []
  Cons = interp.prelude.Cons
  if inspect.isa(s, Cons):
    c = interp.unbox(s[0])
    if c in '+-':
      num.append(c)
      s = s[1]
  have_dot = False
  while inspect.isa(s, Cons):
    c = interp.unbox(s[0])
    if c.isdigit():
      num.append(c)
      s = s[1]
    elif c == '.' and not have_dot:
      have_dot = True
      num.append(c)
      s = s[1]
    else:
      break
  yield getattr(interp.prelude, '(,)')
  yield interp.expr(float(''.join(num) if num else 'nan'))
  yield s

class ParseError(BaseException): pass

def _getchar(interp, s):
  # Get and unbox the head character of a string.  Return a pair of it and the
  # tail.
  if inspect.isa(s, interp.prelude.Cons):
    h,t = s
    return interp.unbox(h), t
  raise ParseError()

def _parseDecChar(interp, s, digits=None):
  '''
  Parses a string of decimal digits.  Returns the corresponding character and
  string tail.
  '''
  digits = digits or []
  s_prev = s
  while True:
    c, s = _getchar(interp, s_prev)
    if c.isdigit():
      digits.append(c)
    elif not digits:
      raise ParseError()
    else:
      return unichr(int(''.join(digits), 10)).encode('utf-8'), s_prev
    s_prev = s

HEXDIGITS = set('0123456789abcdef')
def _parseHexChar(interp, s, digits=None):
  '''
  Parses a string of hexadecimal digits.  Returns the corresponding character
  and string tail.
  '''
  digits = digits or []
  s_prev = s
  while True:
    c, s = _getchar(interp, s_prev)
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
def _parseEscapeCode(interp, s):
  c, s = _getchar(interp, s)
  if c in ESCAPE_CODES:
    return ESCAPE_CODES[c], s
  elif c == 'x': # hex escape code
    return _parseHexChar(interp, s)
  elif c.isdigit(): # decimal escape code
    return _parseDecChar(interp, s, [c])
  else:
    raise ParseError()

def readCharLiteral(interp, s):
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
    yield getattr(interp.prelude, '(,)')

    # Get the character.
    c, s = _getchar(interp, s)
    if c != "'":
      raise ParseError()
    c, s = _getchar(interp, s)
    if c == '\\':
      c_out, s = _parseEscapeCode(interp, s)
    elif ord(c) < 256 and c != "'":
      c_out = c
    else:
      raise ParseError()

    # Eat the closing quote.
    c, s = _getchar(interp, s)
    if c != "'":
      raise ParseError()

    # Second, yield the character as a Curry Char.
    yield interp.expr(c_out)

    # Third, yield the string tail.
    yield s
  except ParseError:
    print "Parse Error!"
    yield interp.expr('\0')
    yield s_in

def readStringLiteral(interp, s):
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
    yield getattr(interp.prelude, '(,)')
    s_out = []
    c, s = _getchar(interp, s)
    if c != '"':
      raise ParseError()
    while True:
      c, s = _getchar(interp, s)
      if c == '\\':
        c, s = _parseEscapeCode(interp, s)
        s_out.append(c)
      elif ord(c) < 256:
        if c == '"':
          yield interp.expr(''.join(s_out))
          yield s
          return
        else:
          s_out.append(c)
      else:
        raise ParseError()
  except ParseError:
    yield interp.expr("")
    yield s_in

def returnIO(interp, a):
  yield interp.prelude.IO
  yield a

def putChar(interp, a):
  interp.stdout.write(conversions.unbox(interp, a))
  yield interp.prelude.IO
  yield runtime.Node(interp.prelude.Unit)

def getChar(interp):
  yield interp.prelude.Char
  yield interp.stdin.read(1)

def generateBytes(stream, chunksize=4096):
  with stream:
    while True:
      chunk = stream.read(chunksize)
      if not chunk:
        return
      for byte in chunk:
        yield byte

def readFile(interp, filename):
  filename = interp.topython(filename)
  stream = open(filename, 'r')
  try:
    import mmap
  except ImportError:
    gen = generateBytes(stream)
  else:
    gen = iter(mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ))
  yield interp.prelude._PyGenerator
  yield gen

def show(interp, arg):
  if inspect.is_boxed(interp, arg):
    string = arg.info.show(arg)
  else:
    string = str(arg)
  if len(string) == 1:
    string = [string]
  result = conversions.expr(interp, string)
  yield interp.prelude._Fwd
  yield result

def apply_hnf(interp, root):
  yield interp.prelude.apply
  yield root[0]
  yield interp.hnf(root, [1])

def normalize(interp, root, path, ground):
  '''Used to implement $!! and $##.'''
  try:
    runtime.hnf(interp, root, path)
  except runtime.E_RESIDUAL:
    if ground:
      raise
    else:
      return root[path]
  target, freevars = runtime.N(interp, root, path=path)
  if ground and freevars:
    raise runtime.E_RESIDUAL(freevars)
  return target

def apply_nf(interp, root):
  yield interp.prelude.apply
  yield root[0]
  yield normalize(interp, root, [1], ground=False)

def apply_gnf(interp, root):
  yield interp.prelude.apply
  yield root[0]
  yield normalize(interp, root, [1], ground=True)

def ensureNotFree(interp, a):
  # This function does nothing when evaluated.  It is, however, a designated
  # symbol that is checked during pull_tabbing.  Pulling a choice past
  # ensureNotFree is an error.
  yield interp.prelude._Fwd
  yield a

def _PyGenerator(interp, gen):
  '''Implements a Python generator as a Curry list.'''
  assert isinstance(gen, collections.Iterator)
  try:
    item = next(gen)
  except StopIteration:
    yield interp.prelude.Nil
  else:
    yield interp.prelude.Cons
    yield interp.expr(item)
    yield interp.expr(gen)
