from .... import icurry
from .... import inspect
from .graph import Node
import numbers

'''Passes isinstance for any node or valid unboxed type.'''
ANY_CURRY_TYPE = (Node, icurry.ILiteral)

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
  this_unboxed = isinstance(ty, (type, tuple))
  arg_boxed = isinstance(arg, Node)
  ok = isinstance(arg, ty) if this_unboxed else inspect.isa(arg, ty)
  if not ok:
    hint = (
        '  (An unboxed value was expected but a boxed value of the '
        'correct type was supplied.  Perhaps you need to wrap an '
        'argument with %s.unboxed?)' % __package__[:__package__.find('.')]
            if this_unboxed and arg_boxed and len(arg) \
                       and _samecategory(arg[0], ty)
            else ''
      )
    raise TypeError(
        'Cannot construct %s %s node from an argument %sof type %s.%s'
            % (_articlefor(name)
              , name
              , '' if p is None else '(in position %s) ' % p
              , arg.info.name if arg_boxed else type(arg).__name__
              , hint
              )
      )

def Char(interp, info, arg):
  '''Typechecker for the Curry Char type.'''
  _typecheck(str, arg, 'Char')
  if len(arg) != 1:
    raise TypeError(
        'Cannot construct a Char node from a str of length %d.' % len(arg)
      )

def Float(interp, info, arg):
  '''Typechecker for the Curry Float type.'''
  _typecheck(float, arg, 'Float')

def Int(interp, info, arg):
  '''Typechecker for the Curry Int type.'''
  _typecheck(int, arg, 'Int')

def Constraint(interp, info, result, constr):
  name = '_Constraint'
  _typecheck(ANY_CURRY_TYPE, result, name)
  _typecheck(getattr(interp.prelude, '(,)'), constr, name, 2)
  _typecheck(interp.prelude._Free, constr[0], name, '2.1')
  if info is interp.prelude._StrictConstraint.info:
    _typecheck(interp.prelude._Free, constr[1], name, '2.2')
  varid = lambda x: inspect.get_id(interp, x)
  if varid(constr[0]) == varid(constr[1]):
    assert constr[0] is constr[1]
    raise TypeError(
        'Cannot construct a _Constraint node relating variable %s to itself.'
            % varid(constr[0])
      )
