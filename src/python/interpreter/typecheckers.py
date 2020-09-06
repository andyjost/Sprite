from .. import icurry
from .. import inspect
from . import runtime
from ..runtime import ChoiceState, UNDETERMINED
import numbers

'''Passes isinstance for any node or valid unboxed type.'''
ANY_CURRY_TYPE = (runtime.Node, icurry.BuiltinVariant)

def _articlefor(name):
  '''Decides (crudely) between the def. articles 'a' and 'an' for a name.'''
  for ch in name:
    if ch.isalpha():
      return 'an' if ch in 'AEIOUaeiou' else 'a'
  return 'a'

def _typecategory(ty):
  '''
  Classify a Python type as integral-, real-, or string-like.  Returns () if
  none of these apply.
  '''
  for cls in (numbers.Integral, numbers.Real, basestring):
    if issubclass(ty, cls):
      return cls
  return ()

def _samecategory(arg, ty):
  '''
  Returns True if ``arg`` belongs to the type category of ``ty``, or if ``ty``
  is a tuple, to that of any of its elements.
  '''
  tys = ty if isinstance(ty, tuple) else (ty,)
  return any(isinstance(arg, _typecategory(ty_)) for ty_ in tys)

def _typecheck(ty, arg, name, p=None):
  unboxed = isinstance(ty, (type, tuple))
  ok = isinstance(arg, ty) if unboxed else inspect.isa(arg, ty)
  if not ok:
    is_boxed = isinstance(arg, runtime.Node)
    hint = (
        '  (An unboxed value was expected but a boxed value of the '
        'correct type was supplied.  Perhaps you need to wrap an '
        'argument with %s.unboxed?)' % __package__[:__package__.find('.')]
            if unboxed and is_boxed and len(arg) and _samecategory(arg[0], ty)
            else ''
      )
    raise TypeError(
        'Cannot construct %s %s node from an argument %sof type %s.%s'
            % (_articlefor(name)
              , name
              , '' if p is None else '(in position %s) ' % p
              , arg.info.name if is_boxed else type(arg).__name__
              , hint
              )
      )

def Char(interp, arg):
  '''Typechecker for the Curry Char type.'''
  _typecheck(str, arg, 'Char')
  if len(arg) != 1:
    raise TypeError(
        'Cannot construct a Char node from a str of length %d.' % len(arg)
      )

def Float(interp, arg):
  '''Typechecker for the Curry Float type.'''
  _typecheck(float, arg, 'Float')

def Int(interp, arg):
  '''Typechecker for the Curry Int type.'''
  _typecheck(int, arg, 'Int')

def EqChoices(interp, result, binding):
  name = '_EqChoices'
  _typecheck(ANY_CURRY_TYPE, result, name)
  _typecheck(getattr(interp.prelude, '(,)'), binding, name, 2)
  _typecheck(int, binding[0], name, '2.1')
  _typecheck(int, binding[1], name, '2.2')

def EqVars(interp, result, binding):
  name = '_EqVars'
  _typecheck(ANY_CURRY_TYPE, result, name)
  _typecheck(getattr(interp.prelude, '(,)'), binding, name, 2)
  _typecheck(interp.prelude._Free, binding[0], name, '2.1')
  _typecheck(interp.prelude._Free, binding[1], name, '2.2')
  varid = lambda x: inspect.get_id(interp, x)
  if varid(binding[0]) == varid(binding[1]):
    assert binding[0] is binding[1]
    raise TypeError(
        'Cannot construct an _EqVars node binding variable %s to itself.'
            % varid(binding[0])
      )

def ChoiceConstr(interp, result, binding):
  name = '_ChoiceConstr'
  _typecheck(ANY_CURRY_TYPE, result, name)
  _typecheck(getattr(interp.prelude, '(,)'), binding, name, 2)
  _typecheck(int, binding[0], name, '2.1')
  _typecheck(ChoiceState, binding[1], name, '2.2')
  if binding[1] == UNDETERMINED:
    raise TypeError(
        'Cannot construct a _ChoiceConstr node from the UNDETERMINED choice '
        'state (in position 2.2).'
      )

