from .. import context
from . import conversions
from .. import exceptions
from .. import inspect
from .. import tags
from ..utility import visitation
import itertools

class Stringifier(object):
  '''Recursively invokes ``show`` on the argument.  Parenthesizes subexpressions.'''
  def stringify(self, arg, **kwds):
    # FIXME: rather than put ? in this list, it would be better to check
    # whether the operation is infix and compare its precedence to the outer
    # expression.
    noparen = (arg.info.name and arg.info.name[0] in '([{<?') or \
        arg.info.tag == tags.T_FWD
    subexprs = self._generate_(arg, noparen)
    format = kwds.pop('format', None)
    if format is None or len(arg) < arg.info.arity:
      return ' '.join(subexprs)
    else:
      subexprs = list(subexprs)
      return format(*subexprs)

  def __call__(self, arg, **kwds):
    return arg.info.show(arg, self)

  def _generate_(self, arg, noparen):
    yield arg.info.name
    for subexpr in arg.successors:
      yield self._recurse_(subexpr, noparen)

  def _recurse_(self, arg, noparen):
    x = self(arg)
    if noparen or not self.__needparens(arg, x):
      return x
    else:
      return '(%s)' % x

  @staticmethod
  def __needparens(arg, x):
    return x and x[0] not in '([{<' and ' ' in x \
       and not (hasattr(arg, 'info') and arg.info.tag == tags.T_FWD)

class ListStringifier(Stringifier):
  '''Formats lists using square brackets rather than applications of Cons.'''
  def __call__(self, arg, **kwds):
    from .. import getInterpreter
    interp = getInterpreter()
    if inspect.isa_list(interp, arg):
      l = []
      try:
        for elem in conversions._listiter(interp, arg):
          l.append(self(elem))
        else:
          return '[%s]' % ', '.join(l)
      except exceptions.NotConstructorError as e:
        return ':'.join(l + [self(e.arg)])
    else:
      return super(ListStringifier, self).__call__(arg, **kwds)


class LitNormalStringifier(Stringifier):
  '''Represents literals in the usual, human-readable, way.'''
  @visitation.dispatch.on('arg')
  def __call__(self, arg, **kwds):
    return super(LitNormalStringifier, self).__call__(arg, **kwds)

  @__call__.when(int)
  def __call__(self, lit, **kwds):
    return str(lit)

  @__call__.when(float)
  def __call__(self, lit, **kwds):
    return str(lit)

  @__call__.when(str)
  def __call__(self, lit, **kwds):
    assert len(lit) == 1
    return str(lit)


class LitUnboxedStringifier(Stringifier):
  '''Represents unboxed literals by appending a #.'''
  @visitation.dispatch.on('arg')
  def __call__(self, arg, **kwds):
    return super(LitUnboxedStringifier, self).__call__(arg, **kwds)

  @__call__.when(int)
  def __call__(self, lit, **kwds):
    return '%r#' % lit # e.g., 1# for unboxed integer 1.

  @__call__.when(float)
  def __call__(self, lit, **kwds):
    return '%r#' % lit

  @__call__.when(str)
  def __call__(self, lit, **kwds):
    assert len(lit) == 1
    return '%r#' % lit


class FreeVarStringifier(Stringifier):
  '''Represents free variables as _a, _b, etc.'''
  def __init__(self, **kwds):
    self.i = itertools.count()
    self.tr = {}

  def __call__(self, arg, **kwds):
    if inspect.isa_freevar(None, arg):
      vid = arg[0]
      if vid not in self.tr:
        alpha = list(self._toalpha(next(self.i)))
        label = '_' + ''.join(reversed(alpha))
        self.tr[vid] = label
      return self.tr[vid]
    else:
      return super(FreeVarStringifier, self).__call__(arg, **kwds)

  @staticmethod
  def _toalpha(n):
    # '_a', '_b', ... '_z', '_aa', '_ab', ...
    assert 0 <= n
    while True:
      yield chr(97 + n % 26)
      n = n // 26 - 1
      if n < 0:
        break

class DefaultStringifier(LitNormalStringifier):
  pass


class ReplStringifier(
    FreeVarStringifier, ListStringifier, LitNormalStringifier
  ):
  '''
  A stringifier for REPL output. This translates free variables into
  identifiers _a, _b, etc. and represents literals in the usual,
  human-readable, way.
  '''
  pass


class Show(object):
  '''Implements the built-in show function.'''
  def __init__(self, format=None):
    self.format = format if callable(format) else \
                  getattr(format, 'format', None) # i.e., str.format.

  def __call__(self, arg, stringifier=None):
    '''
    Converts an expression to a string.

    Parameters:
    -----------
    ``stringify``
        Specifies a callable object used to stringify subexpressions.  This can
        be used to apply arbitrary translations, e.g., from free variables to
        stylized names such as _a, _b, etc.
    '''
    stringifier = stringifier or DefaultStringifier()
    assert isinstance(arg, context.Node)
    return stringifier.stringify(arg, format=self.format)

