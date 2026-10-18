'''Classes for the constructors of a loaded Curry module.'''

import re

from .terms import (
    ConstructorClass, Data, DataClass, Function, Term, Values
  , check_module
  )


def constructor_term(value):
  '''Read a constructor class as its unapplied term.'''
  if isinstance(value, _ConstructorMeta):
    check_module(value.symbol.module)
    if value.symbol._version is not getattr(value.symbol.module, '.version'):
      from ..exceptions import StaleError
      raise StaleError('constructor %s was held before curry.reload(); build it again'
          % value.symbol.fullname)
    return Term.from_symbol(value.symbol._info, value.symbol.module)
  return value


class _ConstructorMeta(type):
  def __getattr__(cls, name):
    # Node builders still read the symbol metadata through a held term.
    return getattr(cls.symbol._info, name)

  def __call__(cls, *args):
    term = constructor_term(cls)
    if args:
      term = term(*args)
    elif cls.symbol.arity:
      return term()
    if len(args) == cls.symbol.arity and _values(args):
      # Literal conversion can contain fromInt or fromRational. Let the
      # evaluator reduce those before converting the constructor's fields.
      value = term._interp.eval(term).one()
      if type(value) is not cls:
        # A newtype is erased by ICurry. Its application still has the
        # constructor's source shape; evaluation keeps the erasure rule.
        result = object.__new__(cls)
        result._value_args = (value,)
      else:
        result = value
      # Construction keeps literal polymorphism. Only an evaluated value
      # fixes its type, as it did before constructor classes.
      result.__dict__.update(term.__dict__)
      return result
    return term

  def __str__(cls): return str(constructor_term(cls))
  def __repr__(cls): return repr(constructor_term(cls))
  def __hash__(cls): return hash(constructor_term(cls))
  def __eq__(cls, other): return constructor_term(cls) == constructor_term(other)
  def __bool__(cls): return bool(constructor_term(cls))


def _forward(name):
  def method(cls, *args):
    return getattr(constructor_term(cls), name)(*args)
  return method


for _name in (
    '__add__', '__radd__', '__sub__', '__rsub__', '__mul__', '__rmul__'
  , '__truediv__', '__rtruediv__', '__floordiv__', '__rfloordiv__'
  , '__mod__', '__rmod__', '__neg__', '__and__', '__rand__'
  , '__choice__', '__rchoice__', '__infix__', '__rinfix__'
  ):
  setattr(_ConstructorMeta, _name, _forward(_name))


# The inspection visitor accepts constructor terms in its second slot.
from ..inspect import _isa

@_isa.when(_ConstructorMeta)
def _constructor_isa(addr, cls):
  return _isa(addr, constructor_term(cls).symbol._info)


def _values(args):
  pending = list(args)
  while pending:
    arg = pending.pop()
    if isinstance(arg, (list, tuple)):
      pending.extend(arg)
    elif isinstance(arg, Term):
      if not isinstance(arg, (Data, Function, Values)):
        return False
    elif not isinstance(arg, (bool, int, float, str)):
      return False
  return True


def _record_fields(module):
  from ..typecheck.exprtype import icurry_filename
  from ..typecheck.sigtable import find_interface
  icy = getattr(module, '.icurry')
  text = icy.metadata.get('all.interface')
  if text is None:
    path = getattr(module, '.interface_file', None)
    if path is None and icy.filename is not None:
      path = find_interface(icy.filename, module.__name__)
    if path is None:
      return {}
    try:
      with open(icurry_filename(path), encoding='utf-8') as stream:
        text = stream.read()
    except OSError:
      return {}
  # The saved Curry interface retains record labels; FlatCurry erases them.
  result = {}
  for declaration in re.findall(r'(?m)^(?:data|newtype)\s+[^;]+;', text):
    for name, body in re.findall(r"([A-Z][A-Za-z0-9_']*)\s*\{([^{}]*)\}", declaration):
      fields = re.findall(r"(?:^|,)\s*([a-z_][A-Za-z0-9_']*(?:\s*,\s*[a-z_][A-Za-z0-9_']*)*)\s*::", body)
      result[name] = tuple(n.strip() for group in fields for n in group.split(','))
  return result


def build_classes(interp, module):
  '''Build once per module version, before the import returns.'''
  metadata = getattr(module, '.info')
  if not getattr(module, '.types'):
    return
  metadata._fields = _record_fields(module)
  for datatype in metadata.types.values():
    # These types cross as Python data or as the result of an IO action.
    if module.__name__ == 'Prelude' and (
        datatype.name in ('Bool', 'Int', 'Float', 'Char', 'IO', '[]', '(->)')
        or datatype.name.startswith('(')
      ):
      datatype.cls = None
      continue
    datatype.cls = type(datatype.name, (DataClass,), {'__module__': module.__name__})
    for symbol in datatype.constructors:
      names = symbol.fields or tuple('_%d' % i for i in range(symbol._info.info.arity))
      attrs = {
          '__module__': module.__name__, '__match_args__': names
        , 'symbol': symbol, 'datatype': datatype
        }
      for index, name in enumerate(names):
        attrs[name] = property(lambda self, index=index: self.args[index])
      cls = _ConstructorMeta(symbol.name, (ConstructorClass, datatype.cls), attrs)
      metadata._classes[symbol.name] = cls


def module_symbol(info, module):
  '''Return the constructor class, nullary value, or ordinary term.'''
  cls = getattr(module, '.info')._classes.get(info.name)
  if cls is None:
    return Term.from_symbol(info, module)
  if cls.symbol.arity:
    return cls
  # A nullary constructor is already in normal form. No evaluation runs.
  from ..interpreter.conversions import ToPython
  term = Term.from_symbol(info, module)
  result = ToPython(interp=term._interp)(term._node)
  result.__dict__.update(term.__dict__)
  return result
