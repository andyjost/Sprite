from . import exceptions, inspect
from .interpreter import conversions
from .utility import visitation
import collections.abc, contextlib, itertools, math

class Stringifier(object):
  '''
  Recursively invokes ``show`` on the argument.

  Two styles are supported.  In 'str' mode, the implementation tries to match
  the output to natural Curry syntax.  Lists, for instance, are written using
  brackets and parentheses are added where needed.  In 'repr' mode, the
  output more closely reflects the node structure of the graph.  Each node
  is written in label-successor form within angle brackets.

  In both modes, cyclical expressions are displayed by replacing
  back-references with ellipses.

  Args:
    style:
      One of 'str' or 'repr'.

  Returns:
    A string.
  '''
  def __init__(self, style='str'):
    self.memo = collections.Counter()
    self.style = str(style)
    if self.style not in ['str', 'repr']:
      raise ValueError(
          'invalid style %r, expected %r or %r' % (self.style, 'str', 'repr')
        )

  @contextlib.contextmanager
  def enter_subexpr(self, arg):
    status = self.push_subexpr(arg)
    try:
      yield status
    finally:
      self.pop_subexpr(arg)

  def push_subexpr(self, arg):
    addr = id(arg)
    self.memo[addr] += 1
    return self.memo[addr] == 1

  def pop_subexpr(self, arg):
    addr = id(arg)
    self.memo[addr] -= 1

  def stringify(self, arg, outer=False, partial=False):
    '''
    Converts the argument to a string according to the specified style.
    Subclasses are expected to override the ``format`` method to apply
    special formatting.

    Unless ``outer`` is True, the result will be parenthesized if it contains
    spaces and does not begin with a bracket-like character.

    If ``partial`` is supplied, the argument treated as a subexpression of a
    partial application.
    '''
    with self.enter_subexpr(arg) as status:
      if not status:
        return '...'
      elif self.style == 'repr':
        if hasattr(arg, 'info'):
          return '<%s>' % ' '.join(self.flatten(arg))
        else:
          return self.format(arg, partial=partial)
      else:
        if inspect.isa_fwd(arg):
          target = inspect.fwd_target(arg)
          return self.stringify(target, outer)
        else:
          string = self.format(arg, partial=partial)
          if not outer and self.__needparens(arg, string):
            return '(%s)' % string
          else:
            return string

  def format(self, arg, **kwds):
    if self.style == 'repr':
      return self.stringify(arg, **kwds)
    else:
      if hasattr(arg, 'info'):
        formatter = getattr(arg.info, 'pyformat', None)
        if formatter is not None and len(arg) == arg.info.arity:
          return formatter.format(*self.flatten(arg))
        else:
          return ' '.join(map(str, self.flatten(arg)))
      elif isinstance(arg, memoryview):
        # The code points of a string literal (see prelude.string.codepoints).
        MAXLEN = 8
        string = ''.join(map(chr, arg[:MAXLEN]))
        elip = '' if len(arg) < MAXLEN else '...'
        return repr(string + elip)
      else:
        return repr(arg)

  def flatten(self, arg):
    # Special cases.  For certain types, including lists and tuples,
    # subexpressions should be treated as outer expressions.  For example, we
    # write [f a] not [(f a)] and (f a, f b) rather than ((f a), (f b)).  For
    # partial applications, do not recurse (the to-string routines will fail
    # for a partial application of ':').
    # if inspect.isa_operator_name(arg.info.name) and self.style != 'repr':
    if arg.info.is_operator and self.style != 'repr':
      # This could be useful, but needs to be controlled.
      #
      # if arg.info.arity == 2:
      #   # Assume binary operators are infix.  ICurry does not have this
      #   # information.
      #   yield self.stringify(arg.successor(0))
      #   yield arg.info.name
      #   yield self.stringify(arg.successor(1))
      #   return
      # else:
      yield '(' + arg.info.name + ')'
    else:
      yield arg.info.name
    treat_subexpr_as_outer = inspect.isa_list(arg) or inspect.isa_tuple(arg)
    for succ in arg.successors:
      yield self.stringify(
          succ, outer=treat_subexpr_as_outer, partial=arg.info.is_partial
        )

  @staticmethod
  def __needparens(arg, string):
    assert not inspect.isa_fwd(arg)
    if inspect.isa_list(arg) or inspect.isa_tuple(arg):
      return False
    elif any(string.startswith(q) and string.endswith(q) for q in '"\''):
      return False
    else:
      return ' ' in string

SYMBOLIC_ESCAPES = {
    ord('\a'): '\\a'
  , ord('\b'): '\\b'
  , ord('\f'): '\\f'
  , ord('\n'): '\\n'
  , ord('\r'): '\\r'
  , ord('\t'): '\\t'
  , ord('\v'): '\\v'
  , ord('"') : '\\"'
  , ord('\\'): '\\\\'
  , ord('\''): '\\\''
  }

def show_float(value):
  '''
  The text of a Float as PAKCS writes it, so that both backends print one
  text (issue #34).

  The digits are the shortest that read back to the same value, the digits
  of ``repr``.  The point stands in the digits when the value is at least
  1.0e-4 and either below 1.0e15 or not integral; otherwise the text is
  d.ddde<exp>, where the exponent carries its sign and no padding, and a
  lone digit gets ".0": 0.0001, 1.0e-5, 10000000.0, 1.0e+15, 1.0e+22.  An
  integral value ends in ".0".  The infinities and NaN, which PAKCS cannot
  make, are written Infinity, -Infinity, and NaN, as KiCS2 writes them.
  The C++ runtime has the same rule in graph/show.cpp.
  '''
  if math.isnan(value):
    return 'NaN'
  sign = '-' if math.copysign(1.0, value) < 0 else ''
  value = abs(value)
  if math.isinf(value):
    return sign + 'Infinity'
  digits, decpt = _float_digits(value)
  n = len(digits)
  if digits == '0':
    text = '0.0'
  elif decpt <= -4 or (decpt > 15 and decpt >= n):
    text = '%s.%se%+d' % (digits[0], digits[1:] or '0', decpt - 1)
  elif decpt <= 0:
    text = '0.' + '0' * -decpt + digits
  elif decpt < n:
    text = digits[:decpt] + '.' + digits[decpt:]
  else:
    text = digits + '0' * (decpt - n) + '.0'
  return sign + text

def _float_digits(value):
  '''
  The shortest digits of a non-negative finite float and the position of
  its point: value = 0.<digits> * 10**decpt.  Zero gives ('0', 0).
  '''
  mantissa, _, exponent = repr(value).partition('e')
  whole, _, fraction = mantissa.partition('.')
  digits = whole + fraction
  stripped = digits.lstrip('0')
  decpt = len(whole) - (len(digits) - len(stripped)) + int(exponent or 0)
  digits = stripped.rstrip('0')
  return (digits, decpt) if digits else ('0', 0)

def escape_char(char, quote):
  '''
  Writes one character as it appears in a literal delimited by ``quote``.
  Printable ASCII is written as is.  Every other code point is written as a
  decimal escape of at least two digits, as PAKCS writes it: show '\\228' is
  "'\\\\228'".
  '''
  codepoint = ord(char)
  if char == quote or char == '\\':
    return '\\' + char
  elif char in '"\'':
    return char
  elif codepoint in SYMBOLIC_ESCAPES:
    return SYMBOLIC_ESCAPES[codepoint]
  elif 0x20 <= codepoint < 0x7f:
    return char
  else:
    return '\\%02d' % codepoint

class ListStringifier(Stringifier):
  '''
  Formats lists using the best style.  Depending on the list type and whether
  it is ground, the style will use square brackets, cons symbols, or
  double-quotes.
  '''
  def format(self, arg, **kwds):
    if self.style != 'repr':
      string = self.format_as_string(arg, **kwds)
      if string is not None:
        return string
    return self.format_as_list(arg, **kwds)

  def format_as_list(self, arg, **kwds):
    '''
    Formats lists using square-bracket-style, when possible; or, if some tail is a
    non-constructor symbol, then using cons symbols.
    '''
    if inspect.isa_cons(arg) and self.style != 'repr' and not kwds.get('partial'):
      l = [self.stringify(arg.successor(0), outer=True)]
      spine = []
      arg = arg.successor(1)
      try:
        while inspect.isa_cons(arg):
          if self.push_subexpr(arg):
            spine.append(arg)
            l.append(self.stringify(arg.successor(0), outer=True))
            arg = arg.successor(1)
          else:
            l.append('...')
            return '[%s]' % ', '.join(l)
        if inspect.isa_nil(arg):
          return '[%s]' % ', '.join(l)
        else:
          l.append(self.stringify(arg))
          return ':'.join(
              '(' + term + ')' if ' ' in term else term
                  for term in l
            )
      finally:
        for arg in reversed(spine):
          self.pop_subexpr(arg)
    else:
      return super(ListStringifier, self).format(arg, **kwds)

  def format_as_string(self, tail, **kwds):
    '''
    A list of Chars is formatted as a double-quoted string.  The list must be
    non-nil, each element must be a ground value of type Prelude.Char or
    unboxed character data, and the list itself must consist of only ground
    values.  If these conditions are not met None is returned.
    '''
    if not kwds.get('partial'):
      chars = ['"']
      while inspect.isa_cons(tail):
        head, tail = tail.successors
        if inspect.isa_char(head):
          ch = inspect.unboxed_value(head)
          chars.append(escape_char(ch, '"'))
        else:
          return
      if len(chars) > 1 and inspect.isa_nil(tail):
        chars.append('"')
        return ''.join(chars)

class LitNormalStringifier(Stringifier):
  '''Represents literals in the usual, human-readable, way.'''
  @visitation.dispatch.on('arg')
  def format(self, arg, **kwds):
    return super(LitNormalStringifier, self).format(arg, **kwds)

  @format.when(int)
  def format(self, lit, **kwds):
    return ('(%r)' if lit<0 else '%r') % lit

  @format.when(float)
  def format(self, lit, **kwds):
    return ('(%s)' if lit<0 else '%s') % show_float(lit)

  @format.when(str)
  def format(self, lit, **kwds):
    assert len(lit) == 1
    return "'%s'" % escape_char(lit, "'")

  @format.when(collections.abc.Iterator)
  def format(self, it, **kwds):
    return str(it)


class LitUnboxedStringifier(Stringifier):
  '''Represents unboxed literals by appending a #.'''
  @visitation.dispatch.on('arg')
  def format(self, arg, **kwds):
    return super(LitUnboxedStringifier, self).format(arg, **kwds)

  @format.when(int)
  def format(self, lit, **kwds):
    return '%r#' % lit # e.g., 1# for unboxed integer 1.

  @format.when(float)
  def format(self, lit, **kwds):
    return '%s#' % show_float(lit)

  @format.when(str)
  def format(self, lit, **kwds):
    assert len(lit) == 1
    return '%r#' % lit


class FreeVarStringifier(Stringifier):
  '''Represents free variables as _a, _b, etc.'''
  def __init__(self, **kwds):
    self.i = itertools.count()
    self.tr = {}
    super(FreeVarStringifier, self).__init__(**kwds)

  def format(self, arg, **kwds):
    if inspect.isa_freevar(arg):
      vid = arg[0]
      if vid not in self.tr:
        alpha = list(self._toalpha(next(self.i)))
        label = '_' + ''.join(reversed(alpha))
        self.tr[vid] = label
      return self.tr[vid]
    else:
      return super(FreeVarStringifier, self).format(arg, **kwds)

  @staticmethod
  def _toalpha(n):
    # '_a', '_b', ... '_z', '_aa', '_ab', ...
    assert 0 <= n
    while True:
      yield chr(97 + n % 26)
      n = n // 26 - 1
      if n < 0:
        break


class DefaultStringifier(
    FreeVarStringifier, ListStringifier, LitNormalStringifier
  ):
  '''
  A stringifier for REPL output. This translates free variables into
  identifiers _a, _b, etc. and represents literals in the usual,
  human-readable, way.
  '''
  pass


class PlainFreeVarsStringifier(ListStringifier, LitNormalStringifier):
  pass


def show(arg, stringifier=None, **kwds):
  '''
  Converts an expression to a string.

  Args:
    stringifier:
        Specifies a callable object used to stringify subexpressions.  This can
        be used to apply arbitrary translations, e.g., from free variables to
        stylized names such as _a, _b, etc.

    kwds:
        As an alternative to supplying the stringifier, when ``stringifier`` is
        None, additional keywords are passed to the constructor of the default
        stringifier.

  Returns:
    The string representation of ``arg``.
  '''
  stringifier = stringifier or DefaultStringifier(**kwds)
  return stringifier.stringify(arg, outer=True)

