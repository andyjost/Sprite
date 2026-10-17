'''Typed Curry terms and the metadata of their names.'''

from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterator, Sequence
import re

from ..common import T_CTOR
from . import CurryNodeInfo

_RAW_ACCESS = ContextVar('curry_raw_symbols', default=False)

@contextmanager
def raw_symbols():
  token = _RAW_ACCESS.set(True)
  try:
    yield
  finally:
    _RAW_ACCESS.reset(token)

_QUALIFIER = re.compile(r"(?<![A-Za-z0-9_'.])(?:[A-Z][A-Za-z0-9_']*\.)+(?=[A-Z])")

def unqualify(text):
  return _QUALIFIER.sub('', text)

class Symbol:
  '''The metadata of a function or constructor, separate from its term.'''
  def __init__(self, info, module):
    self._info = info
    self.module = module

  name = property(lambda self: self._info.name)
  fullname = property(lambda self: self._info.fullname)
  kind = property(lambda self: 'constructor' if self._info.info.tag >= T_CTOR else 'function')
  arity = property(lambda self: self._info.info.arity if self._info.scheme is None
      else self._info.scheme.source_arity)
  signature = property(lambda self: None if self._info.signature is None
      else unqualify(self._info.signature))
  public = property(lambda self: not getattr(self._info.icurry, 'is_private', False))
  fields = None
  info = property(lambda self: self._info.info)

  @property
  def fixity(self):
    from ..typecheck import exprtype
    interp = self._info.interpreter
    interface = interp.sigtable.interface(self.module.__name__)
    if interface is None:
      return None
    try:
      with open(exprtype.icurry_filename(interface.path), encoding='utf-8') as stream:
        text = stream.read()
    except OSError:
      return None
    for assoc, prec, names in re.findall(
        r'^(infixl|infixr|infix)\s+(\d+)\s+(.+?);\s*$', text, re.M
      ):
      if self.name in [n.strip().strip('`') for n in names.split(',')]:
        return '%s %s' % (assoc, prec)
    return None

  def __eq__(self, other):
    return isinstance(other, Symbol) and self._info is other._info

  def __hash__(self):
    return hash(id(self._info))

  def __str__(self):
    return self.name

  def __repr__(self):
    return '<Symbol %s :: %s>' % (self.fullname, self.signature)

class DataType:
  '''The metadata of a data type in a module.'''
  def __init__(self, datatype, module):
    self._datatype = datatype
    self.module = module

  name = property(lambda self: self._datatype.name)
  fullname = property(lambda self: self._datatype.fullname)
  constructors = property(lambda self: tuple(
      getattr(self.module, '.info').symbols[c.name]
        for c in self._datatype.constructors
    ))

  def __getattr__(self, name):
    return getattr(self._datatype, name)

  def __eq__(self, other):
    if isinstance(other, DataType):
      other = other._datatype
    return self._datatype is other

  def __hash__(self):
    return hash(self._datatype)

class ModuleInfo:
  '''Metadata in the module's dotted slot, outside its Curry namespace.'''
  def __init__(self, module):
    self._module = module
    self._symbols = {}
    self._types = {}

  name = property(lambda self: self._module.__name__)

  @property
  def file(self):
    icy = getattr(self._module, '.icurry')
    return None if icy.metadata.get('all.tmpd') is not None else icy.filename

  @property
  def symbols(self):
    for name, info in getattr(self._module, '.symbols').items():
      if not name.startswith(('_impl#', '_inst#')):
        if name not in self._symbols or self._symbols[name]._info is not info:
          self._symbols[name] = Symbol(info, self._module)
    return self._symbols

  @property
  def types(self):
    for name, datatype in getattr(self._module, '.types').items():
      if name not in self._types:
        self._types[name] = DataType(datatype, self._module)
    return self._types

class ValueList(list):
  '''A list value at the new door, including one headed by a symbol.'''

class Char(str):
  '''A Curry character, distinguished from a String.'''
  def __new__(cls, value):
    if not isinstance(value, str) or len(value) != 1:
      raise ValueError('Char takes a str of exactly one character, got %r' % (value,))
    return str.__new__(cls, value)

class Term:
  '''A typed Curry expression held by Python.'''
  __match_args__ = ('symbol', 'args')

  def __init__(self, interp, form, symbol=None, args=(), annotation=None):
    from ..typecheck import builder
    self._interp = interp
    self._form = form
    self.symbol = symbol
    self._args = tuple(args)
    self._annotation = annotation
    with raw_symbols():
      if isinstance(form, CurryNodeInfo) and annotation is None:
        partial = interp.backend.fundamental_symbols.PartApplic if form.info.arity else None
        self._node = interp.backend.make_node(form, partial_info=partial)
        self._spec = None
        self._signature = '?' if form.signature is None else unqualify(form.signature)
        self._defaulted = None
        self.__doc__ = '%s :: %s' % (symbol.fullname, symbol.signature)
        return
      b = builder.TypedBuilder(interp)
      self._spec = b.specs((form,))
      from ..typecheck.defaulting import DefaultingError
      from ..typecheck.errors import ConversionError, ExprTypeMismatchError
      try:
        problem = builder.TypedProblem(b, self._spec, annotation)
      except ExprTypeMismatchError as err:
        if annotation is not None:
          raise
        raise ConversionError(
            err.lines, where=err.where, symbol=err.symbol
          , expected=err.expected, actual=err.actual, value=err.value
          ) from None
      self._signature = unqualify(problem.signature)
      try:
        problem.solve()
      except DefaultingError:
        # The table applies at evaluation; the term keeps its constraints.
        self._node = b.raw_build(form)
        self._defaulted = None
      else:
        self._node = b.materialize(problem)
        self._defaulted = unqualify(builder.show_type(problem.typeexpr))
        builder.record_of(interp).put(self._node, problem.scheme, problem.typeexpr)
    if symbol is not None:
      self.__doc__ = '%s :: %s' % (symbol.fullname, symbol.signature)

  @property
  def args(self):
    if self.symbol is not None:
      return tuple(a if isinstance(a, Term) else Term(self._interp, a) for a in self._args)
    from .. import inspect
    if inspect.isa_cons(self._node):
      return tuple(self._from_node(n) for n in self._node.successors)
    if inspect.isa_tuple(self._node):
      return tuple(self._from_node(n) for n in self._node.successors)
    return ()

  def _from_node(self, node):
    from ..typecheck import builder
    result = object.__new__(Term)
    result._interp = self._interp
    result._node = node
    result._form = node
    result.symbol = None
    result._args = ()
    result._annotation = None
    with raw_symbols():
      result._signature = builder.typeof(self._interp, node)
      result._defaulted = builder.typeof(self._interp, node, True)
    return result

  @classmethod
  def from_symbol(cls, info, module):
    metadata = getattr(module, '.info').symbols
    sym = metadata.get(info.name)
    if sym is None:
      sym = Symbol(info, module)
    return cls(getattr(module, '.interp'), info, sym)

  def __call__(self, *args):
    if not args:
      raise TypeError('a call needs at least one argument; %s alone is the term %s' % (self, self))
    values = tuple(_convert(self._interp, a) for a in args)
    if self.symbol is not None:
      values = self._args + values
      form = [self.symbol._info, *values]
      return Term(self._interp, form, self.symbol, values)
    with raw_symbols():
      apply_ = self._interp.prelude.apply
    head = self
    for arg in values:
      head = Term(self._interp, [apply_, head, arg])
    return head

  def __bool__(self):
    raise TypeError('a Curry term has no truth value; evaluate it: curry.eval(t).one()')

  def __str__(self):
    from .termshow import show
    return show(self)

  def __repr__(self):
    return '<Term %s :: %s>' % (self, self._signature)

  def __eq__(self, other):
    return isinstance(other, Term) and _graph_key(self._node) == _graph_key(other._node)

  def __hash__(self):
    return hash(_graph_key(self._node))

  # The old API reads symbol metadata directly until its removal task.
  def __getattr__(self, name):
    if name in ('successor', 'successors'):
      return getattr(self._node, name)
    if self.symbol is not None:
      return getattr(self.symbol._info, name)
    raise AttributeError(name)


def _graph_key(root):
  from .. import backends, inspect
  seen = {}
  key = []
  pending = [root]
  while pending:
    node = pending.pop()
    if not isinstance(node, backends.Node):
      key.append(('literal', type(node), node))
    elif inspect.isa_freevar(node):
      key.append(('variable', node.id()))
    elif node.id() in seen:
      key.append(('ref', seen[node.id()]))
    else:
      seen[node.id()] = len(seen)
      children = tuple(node.successors)
      key.append(('node', id(node.info), len(children)))
      pending.extend(reversed(children))
  return tuple(key)


def _convert(interp, value):
  from ..expressions import typed
  from ..typecheck.errors import ConversionError
  if isinstance(value, Term):
    return value
  if isinstance(value, Symbol):
    return Term.from_symbol(value._info, value.module)
  if value is None:
    raise ConversionError('cannot convert NoneType: write P.Nothing or P.Just(x)')
  if isinstance(value, bytes):
    raise ConversionError('cannot convert bytes: write b.decode() for the String')
  if isinstance(value, dict):
    raise ConversionError('cannot convert dict: write list(d.items())')
  if isinstance(value, str):
    return typed(str(value), 'Char' if isinstance(value, Char) else '[Char]')
  if isinstance(value, tuple):
    if len(value) == 1 or len(value) > 15:
      raise ConversionError('a Curry tuple has zero or 2 to 15 components')
    return tuple(_convert(interp, x) for x in value)
  if isinstance(value, Sequence):
    return ValueList(_convert(interp, x) for x in value)
  if isinstance(value, bool):
    return typed(value, 'Bool')
  if isinstance(value, float):
    return typed(value, 'Float')
  if isinstance(value, (int, Iterator, CurryNodeInfo)):
    return value
  raise ConversionError('cannot convert %s to a Curry value' % type(value).__name__)


def term(interp, value, type=None):
  if isinstance(value, Term) and type is None:
    return value
  converted = _convert(interp, value)
  if isinstance(converted, Term) and type is None:
    return converted
  result = Term(interp, converted, annotation=type)
  return result
