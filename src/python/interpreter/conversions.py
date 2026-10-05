'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from .. import backends, exceptions, inspect
from ..toolchain.flat2icurry import flatcurry as fc
import numbers

__all__ = ['currytype', 'getconverter', 'topython', 'unbox']

LIST = ('Prelude', '[]')
CHAR = ('Prelude', 'Char')
STRING_NODE = '_biString'

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
  assert isinstance(arg, backends.Node)
  assert inspect.isa_primitive(arg) or inspect.isa_io(arg)
  return arg.successor(0)

def _element_type(typeexpr):
  '''The element type of a list type, or None for an unknown type.'''
  if isinstance(typeexpr, fc.TCons) and typeexpr.name == LIST and typeexpr.args:
    return typeexpr.args[0]
  return None

def _component_types(typeexpr, n):
  '''The component types of a tuple type, or ``n`` unknown types.'''
  if isinstance(typeexpr, fc.TCons) and len(typeexpr.args) == n:
    return typeexpr.args
  return [None] * n

def _is_char(typeexpr):
  return isinstance(typeexpr, fc.TCons) and typeexpr.name == CHAR

def _is_known(typeexpr):
  '''Whether a type is a constructor type; a variable decides nothing.'''
  return isinstance(typeexpr, (fc.TCons, fc.FuncType))

class ToPython(object):
  def __init__(self, convert_freevars=True):
    self.convert_freevars = convert_freevars
  def __call__(self, value, convert_strings=True, typeexpr=None):
    '''Convert one value.'''
    return self.__convert(value, convert_strings, typeexpr)
  def __convert(self, value, convert_strings=True, typeexpr=None):
    if inspect.isa_boxed_primitive(value) or inspect.isa_io(value):
      return unbox(value)
    elif inspect.isa_bool(value):
      return inspect.isa_true(value)
    elif inspect.isa_list(value):
      elemtype = _element_type(typeexpr)
      elems = list(_listiter(value))
      l = [self.__convert(elem, convert_strings, elemtype) for elem in elems]
      if convert_strings:
        # The static type decides when it is known: [Char] is a string,
        # also when it is empty.  Without a type, a list of characters is a
        # string, as it was before the types; a list of strings stays a
        # list.
        if _is_char(elemtype):
          return ''.join(l)
        if not _is_known(elemtype) and l \
            and all(inspect.isa_boxed_char(elem) for elem in elems):
          return ''.join(l)
      return l
    elif inspect.isa_tuple(value):
      comps = _component_types(typeexpr, len(value.successors))
      return tuple(
          self.__convert(x, convert_strings, t)
              for x, t in zip(value.successors, comps)
        )
    elif _is_string_node(value):
      # The string node of the Python backend, not yet unfolded.
      from ..backends.py.currylib.prelude.string import text
      return text(value.successor(0))
    else:
      return value

def _is_string_node(value):
  info = inspect.info_of(value)
  return info is not None and info.name == STRING_NODE \
      and isinstance(value.successor(0), memoryview)

_topython_converter_ = ToPython(convert_freevars=False)

def topython(interp, value, convert_strings=True, exprtype=None):
  '''
  Converts a Curry value to Python by substituting built-in types.

  This functions converts (recursively) the types ``int``, ``float``, ``str``,
  ``bool``, ``list``, and ``tuple``.  Other types are passed through untouched.

  Args:
    value:
        The Curry value to convert.
    convert_strings:
        If True, then lists of characters are converted to Python strings.
    exprtype:
        The static type of the value, in Curry syntax or as a FlatCurry
        type, or None.  The type is threaded through the lists and the
        tuples: an empty list under ``[Char]`` converts to ``''``, while a
        list under a type variable or without a type converts to a string
        when it holds characters.  ``curry.eval`` passes the type of the
        goal it built.

  Raises:
    NotConstructorError:
      Non-ground data was encountered along a list spine.

  Returns:
    The value converted to Python.
  '''
  if isinstance(exprtype, str):
    from ..typecheck import exprtype as exprtype_mod
    exprtype, _ = exprtype_mod.parse_type(interp, exprtype)
  return _topython(value, convert_strings, exprtype)

def _topython(value, convert_strings=True, typeexpr=None):
  '''Internal version of ``topython`` that takes no interpreter.'''
  # This conversion probably ought to depend on the interpreter.  The flags
  # could control how this conversion is performed.  For forward compatibility,
  # it is probably best to require an interpreter even if currently unused.
  value = getattr(value, 'target', value) # handle Variable
  return _topython_converter_(value, convert_strings, typeexpr)

def _listiter(arg):
  '''Iterate through a Curry list.'''
  while inspect.isa_cons(arg):
    yield arg.successor(0)
    arg = arg.successor(1)
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
