'''
Functions for working with Curry expresions.  Handles conversions between Curry
and Python.
'''

from .. import backends, exceptions, inspect
from ..toolchain.flat2icurry import flatcurry as fc
import numbers

__all__ = ['currytype', 'topython', 'unbox']

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
  def __init__(self, convert_freevars=True, variable=None, interp=None):
    self.convert_freevars = convert_freevars
    self.variable = variable
    self.interp = interp
    self.expression_symbols = {} if interp is None else {
        id(symbol.info): symbol
          for module in interp._expression_modules
          for symbol in getattr(module, '.symbols').values()
      }

  def _symbol(self, info):
    from ..typecheck.builder import symbol_map
    return self.expression_symbols.get(id(info)) or symbol_map(self.interp).get(id(info))
  def __call__(self, value, convert_strings=True, typeexpr=None):
    '''Convert one value.'''
    stack = [self._steps(value, convert_strings, typeexpr)]
    result, ready = None, False
    while stack:
      try:
        child, childtype = stack[-1].send(result) if ready else next(stack[-1])
      except StopIteration as done:
        result, ready = done.value, True
        stack.pop()
      else:
        stack.append(self._steps(child, convert_strings, childtype))
        ready = False
    return result

  def _steps(self, value, convert_strings=True, typeexpr=None):
    value = getattr(value, 'target', value)
    if self.variable is not None:
      from ..typecheck.builder import _follow
      value = _follow(value)
      if inspect.isa_freevar(value):
        return self.variable(value)
    if inspect.isa_io(value):
      if isinstance(typeexpr, fc.TCons) and typeexpr.name == fc.prelude('IO') and typeexpr.args:
        typeexpr = typeexpr.args[0]
      return (yield unbox(value), typeexpr)
    if inspect.isa_boxed_primitive(value):
      from ..objects.terms import Char
      return Char(unbox(value)) if inspect.isa_boxed_char(value) else unbox(value)
    elif inspect.isa_bool(value):
      return inspect.isa_true(value)
    elif inspect.isa_list(value):
      elemtype = _element_type(typeexpr)
      elems, cells, tail = [], [], value
      from ..typecheck.builder import _follow
      while inspect.isa_cons(tail):
        cells.append(tail)
        elems.append(_follow(tail.successor(0)))
        tail = _follow(tail.successor(1))
      if not inspect.isa_nil(tail):
        if self.interp is None:
          raise exceptions.NotConstructorError(tail)
        result = yield tail, typeexpr
        for cell, elem in zip(reversed(cells), reversed(elems)):
          converted = yield elem, elemtype
          result = self._value(cell, [converted, result], typeexpr)
        return result
      l = []
      for elem in elems:
        l.append((yield elem, elemtype))
      if convert_strings:
        # The static type decides when it is known: [Char] is a string,
        # also when it is empty.  Without a type, a list of characters is a
        # string, as it was before the types; a list of strings stays a
        # list.
        if _is_char(elemtype) and all(isinstance(x, str) for x in l):
          return ''.join(l)
        if not _is_known(elemtype) and l \
            and all(inspect.isa_boxed_char(elem) for elem in elems):
          return ''.join(l)
      return l
    elif inspect.isa_tuple(value) or inspect.info_of(value) is not None and inspect.isa_tuple_name(value.info.name):
      comps = _component_types(typeexpr, len(value.successors))
      items = []
      for x, t in zip(value.successors, comps):
        items.append((yield x, t))
      return tuple(items)
    elif _is_string_node(value):
      # The string node of the Python backend, not yet unfolded.
      from ..backends.py.currylib.prelude.string import text
      return text(value.successor(0))
    else:
      if self.interp is None or not isinstance(value, backends.Node):
        return value
      from ..typecheck.builder import _partial_parts
      head, stored = _partial_parts(value) if value.info.is_partial else (value.info, value.successors)
      symbol = self._symbol(head)
      if symbol is None:
        return value
      if symbol.fullname == 'Control.SetFunctions.Values':
        from ..objects.terms import Values
        inner = typeexpr.args[0] if isinstance(typeexpr, fc.TCons) and typeexpr.args else None
        items = []
        for x in _listiter(value.successor(0)):
          items.append((yield x, inner))
        result = self._value(value, [items], typeexpr, Values, symbol)
        result._items = tuple(items)
        return result
      scheme = symbol.scheme
      # Function dictionaries are implementation arguments, absent from
      # the value's source application.
      from ..common import T_FUNC
      skip = scheme.ndicts if scheme is not None and head.tag == T_FUNC else 0
      stored = list(stored)[skip:]
      if head.tag == T_FUNC:
        stored = [x for x in stored if isinstance(x, backends.Node) and not _is_dictionary(x)]
      types = _argument_types(scheme, typeexpr, len(stored), value.info.is_partial)
      args = []
      for x, t in zip(stored, types):
        args.append((yield x, t))
      from ..objects.terms import Data, Function
      cls = Function if value.info.is_partial or head.tag == T_FUNC else Data
      return self._value(value, args, typeexpr, cls, symbol)

  def _value(self, node, args, typeexpr, cls=None, symbol=None):
    from ..objects.terms import Data, Symbol, Term, _convert, raw_symbols, unqualify
    from ..typecheck import builder
    if symbol is None:
      symbol = self._symbol(node.info)
    sym = Symbol(symbol, symbol.module)
    result = object.__new__(Data if cls is None else cls)
    result._interp = self.interp
    result._session = self.interp._session
    result._node = node
    result.symbol = sym
    result._value_args = tuple(args)
    # Child terms were just converted in this session. Reuse their metadata
    # without walking their whole subtrees at each enclosing constructor.
    result._args = tuple(a if isinstance(a, Term) else _convert(self.interp, a) for a in args)
    result._form = [symbol, *result._args]
    result._free_vars = {}
    stack = list(reversed(args))
    while stack:
      arg = stack.pop()
      if isinstance(arg, Term):
        result._free_vars.update(arg.free_vars)
      elif isinstance(arg, (list, tuple)):
        stack.extend(reversed(arg))
    with raw_symbols():
      result._signature = unqualify(builder.typeof(self.interp, node)) if typeexpr is None else unqualify(builder.show_type(typeexpr))
      if typeexpr is None:
        b = builder.TypedBuilder(self.interp)
        problem = builder.TypedProblem(b, builder.Raw(node, walk=True))
        typeexpr = problem.typeexpr
    result._typeexpr = typeexpr
    result._defaulted = result._signature
    result._annotation = typeexpr
    return result


def _is_dictionary(node):
  from ..typecheck.builder import _partial_parts, _follow
  node = _follow(node)
  if not isinstance(node, backends.Node):
    return False
  head = _partial_parts(node)[0] if node.info.is_partial else node.info
  return head is not None and head.name.startswith('_inst#')


def _argument_types(scheme, typeexpr, n, partial=False):
  '''Instantiate the constructor's fields from the enclosing value type.'''
  if scheme is None:
    return [None] * n
  params, result = [], scheme.typeexpr
  while isinstance(result, fc.FuncType) and (not partial or len(params) < n):
    params.append(result.domain)
    result = result.range
  mapping = {}
  def match(pattern, actual):
    if isinstance(pattern, fc.TVar) and actual is not None:
      mapping.setdefault(pattern.index, actual)
    elif isinstance(pattern, fc.TCons) and isinstance(actual, fc.TCons) and pattern.name == actual.name:
      for p, a in zip(pattern.args, actual.args): match(p, a)
    elif isinstance(pattern, fc.FuncType) and isinstance(actual, fc.FuncType):
      match(pattern.domain, actual.domain)
      match(pattern.range, actual.range)
  match(result, typeexpr)
  from ..typecheck.defaulting import substitute
  return [substitute(p, mapping) for p in params[:n]] + [None] * max(0, n - len(params))

def _is_string_node(value):
  info = inspect.info_of(value)
  return info is not None and info.name == STRING_NODE \
      and isinstance(value.successor(0), memoryview)

_topython_converter_ = ToPython(convert_freevars=False)

def topython(interp, value, convert_strings=True, exprtype=None):
  '''
  Converts a Curry value to Python by substituting built-in types.

  Built-in values convert recursively to Python data. User constructors,
  functions and set-function results become Data, Function and Values.

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
  return ToPython(convert_freevars=False, interp=interp)(value, convert_strings, exprtype)

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
