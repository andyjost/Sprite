'''
Term classes for the FlatCurry and ICurry data, and two writers: one prints a
term as the ``showTerm`` of PAKCS does, the other as the ``show`` of Haskell
does.

A Curry data value is a constructor application (:class:`Term`), a tuple, a
list, a string (``str``), a character (:class:`Char`), an integer, or a
float.  :func:`showterm` follows the Prolog ``show_term`` of the PAKCS
runtime, which wrote every committed .icy file.  :func:`showhaskell` follows
the derived ``Show`` instances of Haskell, which the Curry front end uses to
write a FlatCurry file; a file read and shown again is byte-identical.
'''

import math

__all__ = [
    'Char', 'Term', 'constructor', 'show_char', 'show_float'
  , 'show_haskell_char', 'show_haskell_float', 'show_haskell_string'
  , 'show_lit_char', 'show_string', 'show_term_char', 'showhaskell', 'showterm'
  ]

class Char(str):
  '''A Curry character.  A plain ``str`` is a Curry string.'''
  __slots__ = ()

  def __new__(cls, value):
    if len(value) != 1:
      raise ValueError('a Char holds one character, got %r' % (value,))
    return str.__new__(cls, value)

  def __repr__(self):
    return 'Char(%s)' % str.__repr__(self)

class Term:
  '''
  A constructor application.  :func:`constructor` makes the subclasses.  Each
  one has a fixed name and a fixed arity.  The arguments are read by field
  name or through ``_args_``.
  '''
  __slots__ = ('_args_',)
  _name_ = 'Term'
  _fields_ = ()

  def __init__(self, *args):
    if len(args) != len(self._fields_):
      raise TypeError(
          '%s takes %d arguments, got %d'
              % (self._name_, len(self._fields_), len(args))
        )
    self._args_ = args

  def __eq__(self, rhs):
    return type(self) is type(rhs) and self._args_ == rhs._args_

  def __ne__(self, rhs):
    return not (self == rhs)

  def __hash__(self):
    return hash((self._name_, self._args_))

  def __repr__(self):
    if not self._fields_:
      return self._name_
    return '%s(%s)' % (self._name_, ', '.join(map(repr, self._args_)))

  def replace(self, **kwds):
    '''A copy of this term with the named fields replaced.'''
    args = list(self._args_)
    for name, value in kwds.items():
      args[self._fields_.index(name)] = value
    return type(self)(*args)

def _getter(i):
  return property(lambda self: self._args_[i])

def constructor(name, fields='', base=Term):
  '''
  Makes a term class.  ``fields`` names the arguments, separated by spaces.
  A class without fields is a nullary constructor.  Make one instance of it
  and use that instance everywhere.
  '''
  fields = tuple(fields.split())
  namespace = {
      '__slots__': (), '_name_': name, '_fields_': fields
    , '__match_args__': fields
    }
  namespace.update((field, _getter(i)) for i, field in enumerate(fields))
  return type(name, (base,), namespace)

# The writer
# ==========
# The escapes of showTermChar in the PAKCS runtime.
_NAMED_ESCAPES = {
    7: '\\a', 8: '\\b', 9: '\\t', 10: '\\n', 11: '\\v', 12: '\\f', 13: '\\r'
  , 34: '\\"', 92: '\\\\'
  }

def show_term_char(code):
  '''
  The text of one character inside a string.  A control character below 32
  gets a two-digit decimal escape.  A character above 126 gets a decimal
  escape.
  '''
  if code in _NAMED_ESCAPES:
    return _NAMED_ESCAPES[code]
  if code < 32:
    return '\\%02d' % code
  if code > 126:
    return '\\%d' % code
  return chr(code)

def show_char(c):
  '''A character literal.  The quote is escaped; the double quote is not.'''
  code = ord(c)
  if code == 39:
    body = "\\'"
  elif code == 34:
    body = '"'
  else:
    body = show_term_char(code)
  return "'%s'" % body

def show_string(s):
  '''A string.  The empty string is the empty list, as in Prolog.'''
  if not s:
    return '[]'
  return '"%s"' % ''.join(show_term_char(ord(c)) for c in s)

def float_digits(f):
  '''
  The shortest decimal digits that read back to the float ``f``, with the
  position of the decimal point: ``abs(f)`` is ``0.<digits>`` times ten to
  the power of the position.  Zero gives ``('0', 1)``.  The sign is left out.
  '''
  text = repr(abs(float(f)))
  mantissa, _, exponent = text.partition('e')
  exponent = int(exponent) if exponent else 0
  whole, _, fraction = mantissa.partition('.')
  digits = whole + fraction
  decpt = len(whole) + exponent
  stripped = digits.lstrip('0')
  decpt -= len(digits) - len(stripped)
  digits = stripped.rstrip('0')
  if not digits:
    digits, decpt = '0', 1
  return digits, decpt

def show_float(f):
  '''
  A float as SWI-Prolog prints it.  The digits are the shortest that read
  back to the same value.  The text has a decimal point.  An exponent is
  used when the point falls more than three places before the digits or
  more than 15 places after them.  A negative float is in parentheses.
  '''
  if not math.isfinite(f):
    raise ValueError('cannot show %r as a Curry float' % (f,))
  sign = '-' if math.copysign(1.0, f) < 0 else ''
  digits, decpt = float_digits(f)
  if decpt <= 0:
    if decpt <= -4:
      body = '%s.%se%d' % (digits[0], digits[1:] or '0', decpt - 1)
    else:
      body = '0.%s%s' % ('0' * -decpt, digits)
  elif len(digits) > decpt:
    body = '%s.%s' % (digits[:decpt], digits[decpt:])
  elif decpt > 15:
    body = '%s.%se+%d' % (digits[0], digits[1:] or '0', decpt - 1)
  else:
    body = '%s%s.0' % (digits, '0' * (decpt - len(digits)))
  text = sign + body
  return '(%s)' % text if f < 0 else text

def showterm(term):
  '''Prints a term as the PAKCS ``showTerm`` does.  There is no newline.'''
  parts = []
  _show(term, parts.append)
  return ''.join(parts)

def _show(x, emit):
  # The walk keeps its own stack of the terms to show and of the text to
  # emit after them, so a term of any depth needs no recursion (issue
  # #125).  An item is a term, or text with the term None.
  stack = [(x, None)]
  while stack:
    x, text = stack.pop()
    if text is not None:
      emit(text)
    elif isinstance(x, Term):
      if not x._args_:
        emit(x._name_)
      else:
        emit('(' + x._name_)
        stack.append((None, ')'))
        for arg in reversed(x._args_):
          stack.append((arg, None))
          stack.append((None, ' '))
    elif isinstance(x, Char):
      emit(show_char(x))
    elif isinstance(x, str):
      emit(show_string(x))
    elif isinstance(x, bool):
      raise TypeError('cannot show %r' % (x,))
    elif isinstance(x, int):
      emit(str(x) if x >= 0 else '(%d)' % x)
    elif isinstance(x, float):
      emit(show_float(x))
    elif isinstance(x, (tuple, list)):
      open_, close = '()' if isinstance(x, tuple) else '[]'
      emit(open_)
      stack.append((None, close))
      for i in reversed(range(len(x))):
        stack.append((x[i], None))
        if i:
          stack.append((None, ','))
    else:
      raise TypeError('cannot show %r' % (x,))

# The Haskell writer
# ==================
# The names of the ASCII control characters, asciiTab of GHC.Show.  Seven of
# them have a letter escape instead (\a, \b, \t, \n, \v, \f, \r), and
# the space is written as itself.
_ASCII_NAMES = [
    'NUL', 'SOH', 'STX', 'ETX', 'EOT', 'ENQ', 'ACK', 'BEL', 'BS', 'HT', 'LF'
  , 'VT', 'FF', 'CR', 'SO', 'SI', 'DLE', 'DC1', 'DC2', 'DC3', 'DC4', 'NAK'
  , 'SYN', 'ETB', 'CAN', 'EM', 'SUB', 'ESC', 'FS', 'GS', 'RS', 'US', 'SP'
  ]
_LETTER_ESCAPES = {
    7: '\\a', 8: '\\b', 9: '\\t', 10: '\\n', 11: '\\v', 12: '\\f', 13: '\\r'
  }

def show_lit_char(code):
  '''
  The text of one character inside a Haskell string or character literal,
  ``showLitChar`` of GHC.Show, and the guard the text needs against the next
  character: ``'0'`` after a decimal escape, which must not run into a digit,
  ``'H'`` after ``\\SO``, else None.  The writer of a string puts ``\\&``
  between the two.  The double quote is not escaped here.
  '''
  if code > 127:
    return '\\%d' % code, '0'
  if code == 127:
    return '\\DEL', None
  if code == 92:
    return '\\\\', None
  if code >= 32:
    return chr(code), None
  if code in _LETTER_ESCAPES:
    return _LETTER_ESCAPES[code], None
  if code == 14:
    return '\\SO', 'H'
  return '\\' + _ASCII_NAMES[code], None

def show_haskell_char(c):
  '''A Haskell character literal.  The quote is escaped; the double quote is not.'''
  code = ord(c)
  if code == 39:
    return "'\\''"
  return "'%s'" % show_lit_char(code)[0]

def show_haskell_string(s):
  '''
  A Haskell string literal, ``showList`` of ``Char``: the double quote is
  escaped, and ``\\&`` separates a decimal escape from a digit and ``\\SO``
  from an ``H``.  The empty string is ``""``.
  '''
  parts = ['"']
  guard = None
  for c in s:
    if guard == '0' and c in '0123456789' or guard == 'H' and c == 'H':
      parts.append('\\&')
    if c == '"':
      text, guard = '\\"', None
    else:
      text, guard = show_lit_char(ord(c))
    parts.append(text)
  parts.append('"')
  return ''.join(parts)

def show_haskell_float(f):
  '''
  A float as the ``show`` of Haskell prints a ``Double``.  The digits are the
  shortest that read back to the same value.  A value from 0.1 up to but not
  including ten million is written with a decimal point and at least one
  digit after it; any other value is written as one digit, a point, the
  other digits, and the exponent after ``e``.  A negative float has a minus
  sign and no parentheses; the caller adds them where Haskell does.
  '''
  if math.isnan(f):
    return 'NaN'
  if math.isinf(f):
    return 'Infinity' if f > 0 else '-Infinity'
  sign = '-' if math.copysign(1.0, f) < 0 else ''
  digits, decpt = float_digits(f)
  if f == 0:
    digits, decpt = '0', 0
  if decpt < 0 or decpt > 7:
    body = '%s.%se%d' % (digits[0], digits[1:] or '0', decpt - 1)
  elif decpt <= 0:
    body = '0.%s%s' % ('0' * -decpt, digits)
  else:
    whole = digits[:decpt] + '0' * (decpt - len(digits))
    body = '%s.%s' % (whole, digits[decpt:] or '0')
  return sign + body

def showhaskell(term):
  '''
  Prints a term as the ``show`` of Haskell does with the derived ``Show``
  instances: the format of the FlatCurry files of the Curry front end.  A
  constructor with arguments is in parentheses when it is an argument; a
  negative number is in parentheses when it is an argument; the elements of
  a list and of a tuple are not.  There is no newline.
  '''
  parts = []
  _show_haskell(term, 0, parts.append)
  return ''.join(parts)

def _show_haskell(x, prec, emit):
  # The walk keeps its own stack, as _show does.  An item is a term with
  # its precedence, or text with the term None.
  stack = [(x, prec, None)]
  while stack:
    x, prec, text = stack.pop()
    if text is not None:
      emit(text)
    elif isinstance(x, Term):
      if not x._args_:
        emit(x._name_)
      else:
        if prec > 10:
          emit('(')
          stack.append((None, 0, ')'))
        emit(x._name_)
        for arg in reversed(x._args_):
          stack.append((arg, 11, None))
          stack.append((None, 0, ' '))
    elif isinstance(x, Char):
      emit(show_haskell_char(x))
    elif isinstance(x, str):
      emit(show_haskell_string(x))
    elif isinstance(x, bool):
      raise TypeError('cannot show %r' % (x,))
    elif isinstance(x, int):
      emit('(%d)' % x if x < 0 and prec > 6 else str(x))
    elif isinstance(x, float):
      text = show_haskell_float(x)
      emit('(%s)' % text if text.startswith('-') and prec > 6 else text)
    elif isinstance(x, (tuple, list)):
      open_, close = '()' if isinstance(x, tuple) else '[]'
      emit(open_)
      stack.append((None, 0, close))
      for i in reversed(range(len(x))):
        stack.append((x[i], 0, None))
        if i:
          stack.append((None, 0, ','))
    else:
      raise TypeError('cannot show %r' % (x,))
