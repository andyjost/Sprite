'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from .. import context, exceptions, inspect
import numbers

__all__ = ['currytype', 'getconverter', 'topython', 'unbox']

def currytype(interp, ty):
  '''
  Gets the Curry type corresponding to a Python type.  For instance, for the
  Python ``bool`` type, this returns the type object for ``Prelude.Bool``.
  '''
  if issubclass(ty, bool):
    return interp.type('Prelude.Bool')
  elif issubclass(ty, str):
    return interp.type('Prelude.Char')
  elif issubclass(ty, numbers.Integral):
    return interp.type('Prelude.Int')
  elif issubclass(ty, numbers.Real):
    return interp.type('Prelude.Float')
  elif issubclass(ty, list):
    return interp.type('Prelude.[]')
  # raise TypeError('cannot convert %r to a Curry type' % ty.__name__)

def unbox(arg):
  '''Unbox a built-in primitive or IO type.'''
  assert isinstance(arg, context.Node)
  assert inspect.isa_primitive(arg) or inspect.isa_io(arg)
  return arg.successors[0]

class ToPython(object):
  def __init__(self, convert_freevars=True):
    self.convert_freevars = convert_freevars
  def __call__(self, value, convert_strings=True):
    '''Convert one value.'''
    return self.__convert(value, convert_strings)
  def __convert(self, value, convert_strings=True):
    if inspect.isa_boxed_primitive(value) or inspect.isa_io(value):
      return unbox(value)
    elif inspect.isa_bool(value):
      return inspect.isa_true(value)
    elif inspect.isa_list(value):
      l = [self.__convert(elem) for elem in _listiter(value)]
      if convert_strings and l:
        try:
          return ''.join(l)
        except TypeError:
          pass
      return l
    elif inspect.isa_tuple(value):
      return tuple(self.__convert(x) for x in value.successors)
    else:
      return value

_topython_converter_ = ToPython(convert_freevars=False)

def topython(interp, value, convert_strings=True):
  '''
  Converts a Curry value to Python by substituting built-in types.

  This functions converts (recursively) the types ``int``, ``float``, ``str``,
  ``bool``, ``list``, and ``tuple``.  Other types are passed through untouched.

  Args:
    value:
        The Curry value to convert.
    convert_strings:
        If True, then lists of characters are converted to Python strings.

  Raises:
    NotConstructorError:
      Non-ground data was encountered along a list spine.

  Returns:
    The value converted to Python.
  '''
  return _topython(value, convert_strings)

def _topython(value, convert_strings=True):
  '''Internal version of ``topython`` that takes no interpreter.'''
  # This conversion probably ought to depend on the interpreter.  The flags
  # could control how this conversion is performed.  For forward compatibility,
  # it is probably best to require an interpreter even if currently unused.
  value = getattr(value, 'target', value) # handle Variable
  return _topython_converter_(value, convert_strings)

def _listiter(arg):
  '''Iterate through a Curry list.'''
  while inspect.isa_cons(arg):
    yield arg.successors[0]
    arg = arg.successors[1]
  if not inspect.isa_nil(arg):
    raise exceptions.NotConstructorError(arg)

def getconverter(converter):
  '''
  Get the converter corresponding to the argument.  The converter returned
  translates free variables into _a, _b, _c, etc.
  '''
  if converter is None or callable(converter):
    return converter
  elif converter == 'topython':
    return topython
    # return ToPython(convert_freevars=True)

