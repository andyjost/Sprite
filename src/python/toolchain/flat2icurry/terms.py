'''
Term classes for the FlatCurry and ICurry data, and a writer that prints a
term as the ``showTerm`` of PAKCS does.

A Curry data value is a constructor application (:class:`Term`), a tuple, a
list, a string (``str``), a character (:class:`Char`), an integer, or a
float.  The writer follows the Prolog ``show_term`` of the PAKCS runtime,
which wrote every committed .icy file.
'''

from ...utility import maxrecursion
import math

__all__ = [
    'Char', 'Term', 'constructor', 'show_char', 'show_float', 'show_string'
  , 'show_term_char', 'showterm'
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

def show_float(f):
  '''
  A float as SWI-Prolog prints it.  The digits are the shortest that read
  back to the same value.  The text has a decimal point.  An exponent is
  used when the point falls more than three places before the digits or
  more than 15 places after them.  A negative float is in parentheses.
  '''
  if not math.isfinite(f):
    raise ValueError('cannot show %r as a Curry float' % (f,))
  text = repr(float(f))
  sign = ''
  if text.startswith('-'):
    sign, text = '-', text[1:]
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
  with maxrecursion():
    _show(term, parts.append)
  return ''.join(parts)

def _show(x, emit):
  if isinstance(x, Term):
    if not x._args_:
      emit(x._name_)
    else:
      emit('(' + x._name_)
      for arg in x._args_:
        emit(' ')
        _show(arg, emit)
      emit(')')
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
    for i, arg in enumerate(x):
      if i:
        emit(',')
      _show(arg, emit)
    emit(close)
  else:
    raise TypeError('cannot show %r' % (x,))
