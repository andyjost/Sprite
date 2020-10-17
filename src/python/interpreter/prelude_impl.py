'''
Implementation of the Prelude externals.
'''
from ..exceptions import *
from . import conversions
from .. import icurry
from .. import inspect
from . import runtime
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

class Comparison(object):
  '''Implements ==, =:=, and Prelude.compare.'''
  def __init__(self, compare, resultinfo, conjunction):
    # A comparison function.  It behaves like ``cmp``, and so returns 0 (or
    # False) for "equal."  It must work on all primitive types (int, float,
    # and char) and node tags.
    self.compare = compare
    # A function taking the results of ``compare`` to node info.
    self.resultinfo = resultinfo
    # The conjunction used to combine terms when recursing.
    self.conjunction = conjunction

  def __call__(self, interp, root):
    lhs, rhs = (interp.hnf(root, [i]) for i in (0,1))
    lhs_isnode, rhs_isnode = (hasattr(x, 'info') for x in root)
    assert lhs_isnode == rhs_isnode # mixing boxed/unboxed -> type error
    if lhs_isnode:
      ltag, rtag = lhs.info.tag, rhs.info.tag
      index = self.compare(ltag, rtag)
      if not index: # recurse when the comparison returns 0 or False.
        arity = lhs.info.arity
        assert arity == rhs.info.arity
        if arity:
          conj = self.conjunction(interp)
          terms = (runtime.Node(root.info, l, r) for l,r in zip(lhs, rhs))
          expr = reduce((lambda a,b: runtime.Node(conj, a, b)), terms)
          yield expr.info
          for succ in expr:
            yield succ
          return
    else:
      index = self.compare(lhs, rhs) # Unboxed comparison.
    yield self.resultinfo(interp, index)

# compare = Comparison( # compare
#     compare=cmp
#   , resultinfo=lambda interp, index:
#         interp.type('Prelude.Ordering').constructors[index+1]
#   , conjunction=lambda interp: interp.prelude.compare_conjunction
#   )
# 
# equals = Comparison( # ==
#     compare=operator.ne # False means equal.
#   , resultinfo=lambda interp, index:
#         interp.prelude.False if index else interp.prelude.True
#   , conjunction=lambda interp: getattr(interp.prelude, '&&')
#   )

equal_constr = Comparison( # =:=
    compare=operator.ne # False means equal.
  , resultinfo=lambda interp, index:
        interp.prelude._Failure if index else interp.prelude.True
  , conjunction=lambda interp: getattr(interp.prelude, '&&')
  )

def compose_io(interp, lhs):
  io_a = interp.hnf(lhs, [0])
  yield interp.prelude.apply
  yield lhs[1]
  yield conversions.unbox(interp, io_a)

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
