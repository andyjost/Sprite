'''Typed Curry terms and the metadata of their names.'''
from ..utility.locking import RLock as _SpriteRLock

import threading, types
from ..typecheck.defaulting import DefaultingError
from ..typecheck.errors import ConversionError, MismatchError, ExprTypeMismatchError
from ..exceptions import StaleError
from ..utility.locking import synchronized, entry
from ..utility import locking


from collections.abc import Collection, Iterator, Sequence
import re
from dataclasses import dataclass

from ..common import T_CTOR
from .. import exceptions
from ..typecheck import builder
from ..toolchain.flat2icurry import flatcurry as fc
from . import CurryNodeInfo, _raw_symbol
from .results import Results

_QUALIFIER = re.compile(r"(?<![A-Za-z0-9_'.])(?:[A-Z][A-Za-z0-9_']*\.)+(?=[A-Z])")

def unqualify(text):
  return _QUALIFIER.sub('', text)

class Symbol:
  '''The metadata of a function or constructor, separate from its term.'''
  def __init__(self, info, module):
    self._info = info
    self.module = module
    self._version = getattr(module, '.version', None)

  name = property(lambda self: self._info.name)
  fullname = property(lambda self: self._info.fullname)
  kind = property(lambda self: 'constructor' if self._info.info.tag >= T_CTOR else 'function')
  arity = property(entry(lambda self: self._info.info.arity if self._info._get_scheme() is None
      else self._info._get_scheme().source_arity))
  signature = property(entry(lambda self: None if self._info._get_signature() is None
      else unqualify(self._info._get_signature())))
  public = property(lambda self: not getattr(self._info.icurry, 'is_private', False))
  fields = property(lambda self: getattr(self.module, '.info')._fields.get(self.name))
  info = property(lambda self: self._info.info)

  @property
  @entry
  def fixity(self):
    from ..typecheck import exprtype
    interp = self._info.interpreter
    interface = interp.sigtable.interface(self.module.__name__)
    if interface is None:
      return None
    generation = getattr(getattr(self.module, '.icurry'), '_loaded_generation', None)
    if generation is not None:
      text = generation.texts.get('.icurry', b'').decode('utf-8')
    else:
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

class _Types(dict):
  def __missing__(self, name):
    from ..exceptions import TypeLookupError
    raise TypeLookupError('no type %r in the module' % name)

class ModuleInfo:
  '''Metadata in the module's dotted slot, outside its Curry namespace.'''
  def __init__(self, module):
    self._module = module
    self._symbols = {}
    self._types = _Types()
    self._classes = {}
    self._fields = {}
    self._terms = {}
    self._cache_lock = _SpriteRLock()

  name = property(lambda self: self._module.__name__)

  @property
  def file(self):
    source = getattr(self._module, '.source_file', None)
    if source is not None:
      return source
    icy = getattr(self._module, '.icurry')
    return None if icy.metadata.get('all.tmpd') is not None else icy.filename

  @property
  @entry
  def symbols(self):
    with self._cache_lock:
      return self._symbol_cache()

  def _symbol_cache(self):
    for name, info in getattr(self._module, '.symbols').items():
      if not name.startswith(('_impl#', '_inst#')):
        if name not in self._symbols or self._symbols[name]._info is not info:
          self._symbols[name] = Symbol(info, self._module)
    return self._symbols

  @property
  @entry
  def types(self):
    with self._cache_lock:
      return self._type_cache()

  def _type_cache(self):
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

class IteratorSource:
  '''The items of a held iterator, shared by its evaluations.'''
  def __init__(self, source):
    self.source = source
    self.items = []
    self.done = False

  def __iter__(self):
    index = 0
    while True:
      if index == len(self.items):
        if self.done:
          return
        try:
          self.items.append(next(self.source))
        except StopIteration:
          self.done = True
          return
      yield self.items[index]
      index += 1

class Term:
  '''A typed Curry expression held by Python.'''
  __match_args__ = ('symbol', 'args')

  @property
  def _signature(self):
    value = self._signature_value
    if callable(value):
      value = self._signature_value = value()
    return value

  @_signature.setter
  def _signature(self, value):
    self._signature_value = value

  @property
  def _defaulted(self):
    value = self._defaulted_value
    if callable(value):
      value = self._defaulted_value = value()
    return value

  @_defaulted.setter
  def _defaulted(self, value):
    self._defaulted_value = value

  @entry
  def __init__(self, interp, form, symbol=None, args=(), annotation=None):
    check_live(form)
    self._interp = interp
    self._session = interp._session
    self._form = form
    self.symbol = symbol
    self._args = tuple(args)
    self._annotation = annotation
    self._dependencies = dependencies(form)
    self._held_vars = tuple(dict.fromkeys(v for v in walk_forms(form) if isinstance(v, Var)))
    self._free_vars = named_vars(form)
    self._has_refs = has_refs(form)
    if self._has_refs:
      self._node = None
      self._signature = '?'
      self._defaulted = None
      return
    if annotation is None and symbol is not None and len(args) == 1 \
        and isinstance(args[0], Term) and self._unary_wrapper(args[0]):
      return
    if isinstance(form, CurryNodeInfo) and annotation is None \
        and (form._get_scheme() is None or not form._get_scheme().context):
      partial = interp.backend.fundamental_symbols.PartApplic if form.info.arity else None
      self._node = interp.backend.make_node(form, partial_info=partial)
      self._spec = None
      self._signature = '?' if form._get_signature() is None else unqualify(form._get_signature())
      self._defaulted = None
      if form._get_scheme() is not None:
        original = form._get_scheme()
        self._scheme = builder.Scheme('<expr>', 'expression', original.typevars,
            (), original.typeexpr, 0, 0)
        self._display_scheme = original
        self._typeexpr = original.typeexpr
        self._variable_types = ()
        self._environment_types = ()
        self._iterator_types = ()
        self._defaulted = lambda t=self._typeexpr: unqualify(builder.show_type(t))
        self._reused_nodes = True
      self.__doc__ = '%s :: %s' % (symbol.fullname, symbol.signature)
      return
    b = builder.TypedBuilder(interp, reuse_terms=True)
    self._spec = b.specs((form,))
    try:
      try:
        problem = builder.TypedProblem(b, self._spec, annotation)
      except exceptions.CurryTypeError:
        if not b._held:
          raise
        # Diagnose from the original form so nested argument positions
        # and the established exception sentences remain unchanged.
        b = builder.TypedBuilder(interp)
        b.reuse_terms = False
        self._spec = b.specs((form,))
        problem = builder.TypedProblem(b, self._spec, annotation)
    except ExprTypeMismatchError as err:
      if annotation is not None:
        raise
      error = MismatchError if _has_term(form) else ConversionError
      lines = err.lines
      if error is MismatchError and err.where:
        from ..typecheck.sigtable import show_type
        lines = 'type mismatch in %s: expected %s, got %s' % (
            err.where, show_type(err.expected), show_type(err.actual))
      raise error(
          lines, where=err.where, symbol=err.symbol
        , expected=err.expected, actual=err.actual, value=err.value
        ) from None
    fix_variable_types(problem)
    self._signature = signature(problem)
    self._display_scheme = problem.display_scheme
    if not problem.frees and not problem._env_vars:
      self._scheme, naming = problem.scheme, None
    else:
      self._scheme, naming = problem._make_scheme()
    self._variable_types = tuple((spec.payload,
        builder.terms.zonk(spec.type, naming, problem.arity)) for spec in problem.frees)
    self._environment_types = tuple(builder.terms.zonk(t, naming, problem.arity)
        for t in problem._env_vars)
    self._iterator_types = tuple(builder.terms.zonk(spec.elem, naming, problem.arity)
        for spec in problem.iters)
    self._typeexpr = None
    self._ambiguous = getattr(problem, 'ambiguous', None)
    try:
      problem.solve()
    except DefaultingError:
      # The table applies at evaluation; the term keeps its constraints.
      self._node = b.raw_build(form)
      self._defaulted = None
    else:
      fix_variable_types(problem)
      self._node = b.materialize(problem)
      self._typeexpr = problem.typeexpr
      self._defaulted = unqualify(builder.show_type(self._typeexpr))
      builder.record_of(interp).put(self._node, problem.scheme, self._typeexpr)
    self._reused_nodes = not b._specialized
    if isinstance(form, CurryNodeInfo) and annotation is None:
      # The raw-expression door exposes the unapplied symbol. Keep its
      # defaulted graph separately for the typed construction/eval path.
      self._typed_node = self._node
      partial = interp.backend.fundamental_symbols.PartApplic if form.info.arity else None
      self._node = interp.backend.make_node(form, partial_info=partial)
    if symbol is not None:
      self.__doc__ = '%s :: %s' % (symbol.fullname, symbol.signature)

  def _unary_wrapper(self, child):
    '''Extend a -> T a by one node and one persistent type constructor.

    No inference or traversal of the child's type is needed for this
    substitution. Type text is rendered only when the public API asks.
    '''
    if getattr(child, '_typeexpr', None) is None or getattr(child, '_scheme', None) is None:
      return False
    info = self.symbol._info
    scheme = info._get_scheme()
    if info.info.tag < T_CTOR or info.info.arity != 1 or scheme is None or scheme.context:
      return False
    t = scheme.typeexpr
    if not isinstance(t, fc.FuncType) or not isinstance(t.domain, fc.TVar) \
        or not isinstance(t.range, fc.TCons) or t.range.args != [t.domain]:
      return False
    if isinstance(self._interp.sigtable.type_decl('%s.%s' % t.range.name), fc.TypeNew):
      return False
    wrap = lambda value: fc.TCons(t.range.name, [value])
    original = child._scheme
    self._scheme = builder.Scheme('<expr>', 'expression', original.typevars,
        original.context, wrap(original.typeexpr), 0, len(original.context))
    display = child._display_scheme
    self._display_scheme = builder.Scheme('<expr>', 'expression', display.typevars,
        display.context, wrap(display.typeexpr), 0, len(display.context))
    self._typeexpr = wrap(child._typeexpr)
    self._variable_types = child._variable_types
    self._environment_types = child._environment_types
    self._iterator_types = child._iterator_types
    self._spec = None
    self._node = self._interp.backend.make_node(info, getattr(child, '_typed_node', child._node))
    self._signature = lambda scheme=self._display_scheme: unqualify(str(scheme))
    self._defaulted = lambda typeexpr=self._typeexpr: unqualify(builder.show_type(typeexpr))
    self._reused_nodes = True
    builder.record_of(self._interp).put(self._node, self._scheme, self._typeexpr)
    self.__doc__ = '%s :: %s' % (self.symbol.fullname, self.symbol.signature)
    return True

  free_vars = property(lambda self: dict(self._free_vars))

  @property
  @entry
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
    result = object.__new__(Term)
    result._interp = self._interp
    result._session = self._session
    result._node = node
    result._form = node
    result.symbol = None
    result._args = ()
    result._free_vars = {}
    result._annotation = None
    result._signature = builder.typeof(self._interp, node)
    result._defaulted = builder.typeof(self._interp, node, True)
    return result

  @classmethod
  def from_symbol(cls, info, module):
    locking.check_entry()
    metadata = getattr(module, '.info')
    name = info.name
    with metadata._cache_lock:
      held = metadata._terms.get(name)
      version = getattr(module, '.version')
      if held is None or held.symbol._info is not info or held.symbol._version is not version:
        sym = metadata._symbols.get(name)
        if sym is None or sym._info is not info:
          sym = metadata._symbols[name] = Symbol(info, module)
        held = None
    if held is None:
      candidate = cls(getattr(module, '.interp'), info, sym)
      scheme = info._get_scheme()
      arity = info.info.arity if scheme is None else scheme.source_arity
      candidate._fresh_computation = info.info.tag < T_CTOR and arity == 0
      with metadata._cache_lock:
        if getattr(module, '.version') is not version:
          raise StaleError('the module was reloaded while accessing a symbol')
        held = metadata._terms.get(name)
        if held is None or held.symbol._info is not info or held.symbol._version is not version:
          held = metadata._terms[name] = candidate
    # Native construction and copies can wait for the heap. Only cache
    # inspection/publication above holds the metadata lock.
    result = object.__new__(cls)
    result.__dict__.update(held.__dict__)
    if held._fresh_computation:
      result._node = held._node.copy()
      if hasattr(held, '_typed_node'):
        result._typed_node = held._typed_node.copy()
    return result

  @entry
  def __call__(self, *args):
    check_live(self)
    if not args:
      raise TypeError('a call needs at least one argument; %s alone is the term %s' % (self, self))
    values = []
    for index, arg in enumerate(args, len(self._args) + 1):
      try:
        values.append(_convert(self._interp, arg))
      except ConversionError as error:
        if self.symbol is None:
          raise
        where = 'argument %d of %s :: %s' % (
            index, self.symbol.fullname, self.symbol.signature)
        raise ConversionError('cannot convert %r at %s: %s' % (arg, where, error),
            where=where, symbol=self.symbol.fullname, value=arg) from None
    values = tuple(values)
    if self.symbol is not None:
      values = self._args + values
      form = [self.symbol._info, *values]
      try:
        return Term(self._interp, form, self.symbol, values)
      except (ConversionError, MismatchError) as error:
        pattern = r'argument (\d+) of ' + re.escape(self.symbol.fullname) + r' :: '
        match = re.match(pattern, error.where or '')
        if match:
          index = int(match[1]) - 1
          inputs = (*self._args, *args)
          if index < len(inputs):
            if isinstance(error, MismatchError) and not isinstance(inputs[index], float):
              raise
            raise _conversion_error(error, inputs[index]) from None
        raise
    apply_ = _raw_symbol(self._interp._prelude, 'apply')
    head = self
    for arg in values:
      head = Term(self._interp, [apply_, head, arg])
    return head

  @entry
  def __choice__(self, other):
    return choice(self._interp, self, other)

  @entry
  def __rchoice__(self, other):
    return choice(self._interp, other, self)

  @entry
  def _op(self, name, left, right):
    try:
      _convert(self._interp, left)
      _convert(self._interp, right)
    except ConversionError:
      return NotImplemented
    return self._interp._prelude[name](left, right)

  def __add__(self, other): return self._op('+', self, other)
  def __radd__(self, other): return self._op('+', other, self)
  def __sub__(self, other): return self._op('-', self, other)
  def __rsub__(self, other): return self._op('-', other, self)
  def __mul__(self, other): return self._op('*', self, other)
  def __rmul__(self, other): return self._op('*', other, self)
  def __truediv__(self, other): return self._op('/', self, other)
  def __rtruediv__(self, other): return self._op('/', other, self)
  def __floordiv__(self, other): return self._op('div', self, other)
  def __rfloordiv__(self, other): return self._op('div', other, self)
  def __mod__(self, other): return self._op('mod', self, other)
  def __rmod__(self, other): return self._op('mod', other, self)
  def __and__(self, other): return self._op('&', self, other)
  def __rand__(self, other): return self._op('&', other, self)
  @entry
  def __neg__(self): return self._interp._prelude.negate(self)

  def __infix__(self, op, other):
    return self._infix(op, other, False)

  def __rinfix__(self, op, other):
    return self._infix(op, other, True)

  @entry
  def _infix(self, op, other, reflected):
    modules = [self._interp._prelude]
    for value in walk_forms((self, other)):
      if isinstance(value, Term):
        held = ([value.symbol.module] if value.symbol is not None else [])
        held.extend(module for module, version in getattr(value, '_dependencies', ()))
        for module in held:
          if module not in modules:
            modules.append(module)
    for module in modules:
      if op in getattr(module, '.symbols'):
        try:
          _convert(self._interp, other)
        except ConversionError:
          return NotImplemented
        return module[op](other, self) if reflected else module[op](self, other)
    return NotImplemented

  def __bool__(self):
    raise TypeError('a Curry term has no truth value; evaluate it: curry.eval(t).one()')

  @entry
  def __str__(self):
    from .termshow import show
    return show(self)

  @entry
  def __repr__(self):
    return '<Term %s :: %s>' % (self, self._signature)

  @entry
  def __eq__(self, other):
    from .classes import constructor_term
    other = constructor_term(other)
    if isinstance(other, Var):
      return self is other
    return isinstance(other, Term) and _graph_key(self._node, variable_nodes(self)) == _graph_key(other._node, variable_nodes(other))

  @entry
  def __hash__(self):
    return hash(_graph_key(self._node, variable_nodes(self)))

  # The old API reads symbol metadata directly until its removal task.
  def __getattr__(self, name):
    if name in ('successor', 'successors'):
      locking.check_entry()
      return getattr(self._node, name)
    if self.symbol is not None:
      return getattr(self.symbol._info, name)
    raise AttributeError(name)


class Data(Term):
  '''A constructor value with converted arguments.'''
  args = property(lambda self: self._value_args)

  def __bool__(self):
    return True

  def __repr__(self):
    return str(self)

  @entry
  def _compare(self, other, accepted):
    if not isinstance(other, Data):
      return NotImplemented
    from ..exceptions import CurryTypeError
    try:
      result = self._interp._eval(self._interp._prelude.compare(self, other)).one()
    except CurryTypeError:
      raise TypeError('ordering Data requires an Ord instance for its type') from None
    return result.symbol.name in accepted

  def __lt__(self, other): return self._compare(other, ('LT',))
  def __le__(self, other): return self._compare(other, ('LT', 'EQ'))
  def __gt__(self, other): return self._compare(other, ('GT',))
  def __ge__(self, other): return self._compare(other, ('GT', 'EQ'))


class Function(Term):
  '''A function value, including a partial constructor application.'''
  args = property(lambda self: self._value_args)

  @entry
  def __call__(self, *args):
    if not args:
      return super().__call__()
    check_live(self)
    apply_ = _raw_symbol(self._interp._prelude, 'apply')
    result = self
    for arg in args:
      result = Term(self._interp, [apply_, result, _convert(self._interp, arg)])
    return result

  def __bool__(self):
    return True

  def __repr__(self):
    return '<Function %s :: %s>' % (self, self._signature)


class DataClass(Data):
  '''The base of the values of one loaded Curry data type.'''


class ConstructorClass(DataClass):
  '''The base of the values of one loaded Curry constructor.'''


class Values(Term, Collection):
  '''The finite multiset produced by a set function.'''
  def __len__(self): return len(self._items)
  def __iter__(self): return iter(self._items)
  def __contains__(self, value): return value in self._items
  def __bool__(self): return bool(self._items)
  def __repr__(self): return str(self)

  def __eq__(self, other):
    if not isinstance(other, Values):
      return Term.__eq__(self, other)
    remaining = list(other)
    for item in self:
      for index, candidate in enumerate(remaining):
        if item == candidate:
          remaining.pop(index)
          break
      else:
        return False
    return not remaining

  __hash__ = None


def variable_nodes(term):
  from ..typecheck.builder import _follow
  out = {}
  for value in walk_forms(term):
    if isinstance(value, Var):
      node = value._marker._shared(value._interp)
      if node is not None:
        out[node.id()] = id(value)
        out[_follow(node).id()] = id(value)
  return out


def _graph_key(root, variables=None):
  from .. import backends, inspect
  from ..backends.cxx import curryrtbindings as curryrt
  seen = {}
  key = []
  pending = [root]
  while pending:
    node = pending.pop()
    if isinstance(node, tuple) and len(node) == 2 and node[0] == 'leave':
      seen.pop(node[1])
      continue
    if not isinstance(node, backends.Node):
      key.append(('literal', type(node), node))
    elif variables and node.id() in variables:
      key.append(('variable', variables[node.id()]))
    elif inspect.isa_freevar(node):
      key.append(('variable', node.id()))
    elif curryrt.is_handle(node.info):
      key.append(('Handle', node.successor(0)))
    elif curryrt.is_io_ref(node.info):
      key.append(('IORef', node.id()))
    elif node.id() in seen:
      key.append(('ref', seen[node.id()]))
    else:
      seen[node.id()] = len(seen)
      children = tuple(node.successors)
      info = node.info
      identity = ('partial', info.arity) if info.is_partial else id(info)
      key.append(('node', identity, len(children)))
      # Constructor sharing does not distinguish equal data values. Keep
      # ancestors until their children finish, so cycles still terminate.
      if inspect.isa_ctor(node):
        pending.append(('leave', node.id()))
      pending.extend(reversed(children))
  return tuple(key)


def _has_term(value):
  if isinstance(value, Term):
    return True
  if isinstance(value, (list, tuple)):
    return any(_has_term(v) for v in value)
  return False


def _conversion_error(error, value):
  from ..typecheck.sigtable import show_type
  expected = show_type(error.expected) if error.expected is not None else None
  if expected is None:
    return error
  hint = None
  if isinstance(value, str) and not isinstance(value, Char):
    hint = 'a str is a String'
    if expected == 'Char':
      hint += '; write curry.Char(%r)' % value
  elif isinstance(value, bool):
    hint = 'a bool is a Bool'
  elif isinstance(value, int):
    hint = 'an int is a numeric literal'
    if expected == 'Bool':
      hint += '; write True or False'
  elif isinstance(value, float) and expected == 'Int':
    hint = 'a float is a Float; write an int for an Int slot'
  if hint is None:
    return error
  message = 'cannot convert %r to %s at %s: %s' % (value, expected, error.where, hint)
  symbol = error.symbol
  if symbol is None and error.where and ' of ' in error.where:
    symbol = error.where.split(' of ', 1)[1].split(' :: ', 1)[0]
  return ConversionError(message, where=error.where, symbol=symbol,
      expected=error.expected, actual=error.actual, value=value)


def _convert(interp, value):
  # Containers can be deeper than the Python call stack. Convert their
  # elements in source order and assemble tuples after their children.
  root = [None]
  stack = [(value, root, 0, False)]
  while stack:
    value, target, index, finish = stack.pop()
    if finish:
      target[index] = tuple(value)
    elif isinstance(value, (tuple, Sequence)) and not isinstance(value, (str, bytes)):
      if isinstance(value, tuple) and (len(value) == 1 or len(value) > 15):
        raise ConversionError('a Curry tuple has zero or 2 to 15 components')
      converted = ValueList([None] * len(value))
      if isinstance(value, tuple):
        stack.append((converted, target, index, True))
      else:
        target[index] = converted
      stack.extend((value[i], converted, i, False)
          for i in reversed(range(len(value))))
    else:
      target[index] = _convert_leaf(interp, value)
  return root[0]


def _convert_leaf(interp, value):
  from .classes import constructor_term
  value = constructor_term(value)
  from ..expressions import typed
  if value is anonymous:
    var = Var(interp)
    var._anonymous = True
    return var
  if isinstance(value, Term):
    check_live(value)
    return value
  if isinstance(value, Results):
    raise ConversionError('cannot convert Results to a Curry list: write list(results)')
  choice_type = getattr(types, 'ChoiceType', ())
  if isinstance(value, choice_type):
    return choice(interp, value.lhs, value.rhs)
  if isinstance(value, Symbol):
    return Term.from_symbol(value._info, value.module)
  if value is None:
    raise ConversionError('cannot convert NoneType: write P.Nothing or P.Just(x)')
  if isinstance(value, bytes):
    raise ConversionError('cannot convert bytes: write b.decode() for the String')
  if isinstance(value, dict):
    raise ConversionError('cannot convert dict: write list(d.items())')
  if isinstance(value, str):
    return typed(str.__str__(value), 'Char' if isinstance(value, Char) else '[Char]')
  if isinstance(value, bool):
    return typed(value, 'Bool')
  if isinstance(value, float):
    return typed(value, 'Float')
  if isinstance(value, IteratorSource):
    return value
  if isinstance(value, Iterator):
    return IteratorSource(value)
  if isinstance(value, (int, CurryNodeInfo)):
    return value
  raise ConversionError('cannot convert %s to a Curry value' % type(value).__name__)


def term(interp, value, type=None):
  check_live(value)
  check_refs(value)
  if isinstance(value, Term) and type is None:
    return value
  converted = _convert(interp, value)
  if isinstance(converted, Term) and type is None:
    return converted
  result = Term(interp, converted, annotation=type)
  return result


class Anonymous:
  """A fresh variable at each occurrence in a term."""
  def __repr__(self):
    return 'curry.anonymous'

anonymous = Anonymous()

class Var(Term):
  """One Python object, one free variable, with a persistent static type."""
  @entry
  def __init__(self, interp, name=None, type=None):
    from ..expressions import free
    if name is not None and not re.fullmatch(r"[a-z_][A-Za-z0-9_']*", name):
      raise ValueError('%r is not a Curry variable name' % name)
    self.name = name
    self._marker = free(exprtype=type)
    self._marker._var = self
    self._interp = interp
    self._session = interp._session
    self._form = self._marker
    self._args = ()
    self.symbol = None
    self._annotation = None
    self._free_vars = {} if name is None else {name: self}
    self._signature = 'Data a => a' if type is None else type
    self._defaulted = None
    if type is not None:
      b = builder.TypedBuilder(interp)
      builder.TypedProblem(b, b.specs((self,)))

  @property
  def _node(self):
    from ..expressions import untyped_expr
    return untyped_expr(self._interp, self._marker)

  def __eq__(self, other): return self is other
  def __hash__(self): return id(self)
  def __repr__(self): return str(self)

@dataclass
class LetForm:
  body: object
  bindings: dict

class Reference(Term):
  """A binding reference, resolved only by its enclosing let."""
  @entry
  def __init__(self, interp, name):
    self._interp = interp
    self._session = interp._session
    self.name = name
    self._form = self
    self._node = None
    self.symbol = None
    self._args = ()
    self._annotation = None
    self._free_vars = {}
    self._signature = '?'
    self._defaulted = None


def walk_forms(root):
  from ..expressions import typed
  seen = set()
  stack = [root]
  while stack:
    value = stack.pop()
    yield value
    if isinstance(value, Term):
      if id(value) in seen or isinstance(value, Reference):
        continue
      seen.add(id(value))
      if hasattr(value, '_text'):
        stack.extend(reversed(list(value.free_vars.values())))
      elif hasattr(value, '_held_vars') and not getattr(value, '_has_refs', False):
        stack.extend(reversed(value._held_vars))
      else:
        stack.append(value._form)
    elif isinstance(value, (list, tuple)):
      stack.extend(reversed(value))
    elif isinstance(value, LetForm):
      stack.extend(reversed([value.body, *value.bindings.values()]))
    elif isinstance(value, typed):
      stack.append(value.value)


def named_vars(root):
  from ..expressions import free
  from ..exceptions import CurryTypeError
  out = {}
  for value in walk_forms(root):
    var = value if isinstance(value, Var) else getattr(value, '_var', None) if isinstance(value, free) else None
    if var is not None and var.name is not None:
      if var.name in out and out[var.name] is not var:
        raise CurryTypeError('two different variables named %r in one goal; name one differently' % var.name)
      out[var.name] = var
  return out


def check_module(module):
  from ..utility.procfork import check
  check()
  interp = getattr(module, '.interp')
  name = module.__name__
  if getattr(module, '.session') is not interp._session:
    raise StaleError('module %s was held before curry.reset(); build it again from %s' % (name, name))
  if getattr(module, '.retired', False):
    raise StaleError('module %s was held before curry.reload(%s); build it again from %s' % (name, name, name))


def check_term(value):
  if value._session is not value._interp._session:
    name = value.symbol.module.__name__ if value.symbol is not None else None
    rebuild = 'build it again' if name is None else 'build it again from %s' % name
    raise StaleError('the term%s was built before curry.reset(); %s'
        % ('' if name is None else ' of module %s' % name, rebuild))
  if value.symbol is not None:
    check_module(value.symbol.module)
    if value.symbol._version is not getattr(value.symbol.module, '.version'):
      name = value.symbol.module.__name__
      raise StaleError('the term of module %s was built before curry.reload(%s); build it again from %s'
          % (name, name, name))
  for module, version in getattr(value, '_dependencies', ()):
    check_module(module)
    if version is not getattr(module, '.version'):
      name = module.__name__
      raise StaleError('the term of module %s was built before curry.reload(%s); build it again from %s'
          % (name, name, name))


def dependencies(root):
  '''The distinct module generations a form holds, including its children.'''
  found = {}
  for value in walk_forms(root):
    if isinstance(value, Term):
      entries = list(getattr(value, '_dependencies', ()))
      if value.symbol is not None:
        entries.append((value.symbol.module, value.symbol._version))
    elif isinstance(value, CurryNodeInfo) and value.module is not None:
      entries = [(value.module, getattr(value.module, '.version'))]
    else:
      continue
    for module, version in entries:
      found[id(module), id(version)] = (module, version)
  return tuple(found.values())


def check_live(root):
  from ..utility.procfork import check
  check()
  from . import CurryModule
  from .classes import constructor_term
  for value in walk_forms(root):
    value = constructor_term(value)
    if isinstance(value, Term):
      check_term(value)
    elif isinstance(value, CurryModule):
      check_module(value)
    elif isinstance(value, CurryNodeInfo) and value.module is not None:
      check_module(value.module)


def has_refs(root):
  from ..expressions import typed
  stack, seen = [root], set()
  while stack:
    value = stack.pop()
    if isinstance(value, Reference):
      return True
    if isinstance(value, Term):
      if id(value) not in seen:
        seen.add(id(value))
        if hasattr(value, '_has_refs'):
          if value._has_refs:
            return True
        else:
          stack.append(value._form)
    elif isinstance(value, (list, tuple)):
      stack.extend(value)
    elif isinstance(value, typed):
      stack.append(value.value)
  return False


def check_refs(root):
  from ..exceptions import CurryTypeError
  if has_refs(root):
    names = [v.name for v in walk_forms(root) if isinstance(v, Reference)]
    raise CurryTypeError('references %s need bindings in curry.let' % ', '.join(names))


def fix_variable_types(problem):
  '''Keep inferred type structure before defaulting chooses dictionaries.'''
  from ..typecheck import terms
  for spec in problem.frees:
    marker = spec.payload
    if getattr(marker, '_var', None) is not None:
      t = terms.whnf(spec.type, problem.arity)
      if not isinstance(t, terms.Var):
        # Type work stays private. Commit a compatible type under the
        # marker lock: two first uses cannot overwrite incompatible types.
        inferred = terms.zonk(t, arity=problem.arity)
        with marker._type_lock:
          previous = marker.exprtype
          if previous is not None and not isinstance(previous, str):
            from ..typecheck.unify import unify, UnifyError
            old = terms.instantiate(previous, {})
            new = terms.instantiate(inferred, {})
            try:
              unify(old, new)
            except UnifyError:
              from ..typecheck.sigtable import show_type
              raise MismatchError('type mismatch in shared free variable: expected %s, got %s'
                  % (show_type(previous), show_type(inferred))) from None
            inferred = terms.zonk(new)
          marker.exprtype = inferred
          from ..typecheck.sigtable import show_type
          marker._var._signature = unqualify(show_type(inferred))


def signature(problem):
  """Include Data for polymorphic free variables, as a free declaration does."""
  if not problem.frees:
    scheme, _ = problem._undefaulted()
    problem.scheme = problem.display_scheme = scheme
    return unqualify(str(scheme))
  from ..typecheck.instances import DATA_CLASS, Pred, NoInstance
  from ..typecheck import terms
  from ..toolchain.flat2icurry import flatcurry as fc
  from ..typecheck.errors import AmbiguousTypeError
  frees = [terms.prune(spec.type) for spec in problem.frees]
  env = problem._env_vars
  problem._env_vars = [v for v in env if all(terms.prune(v) is not fv for fv in frees)]
  try:
    problem._undefaulted()
  except AmbiguousTypeError as error:
    problem.ambiguous = error
    problem._env_vars = env
    problem._undefaulted()
  finally:
    problem._env_vars = env
  predicates = list(problem._live())
  seen = {(p.classname, id(terms.prune(p.term))) for p in predicates}
  for spec in problem.frees:
    if isinstance(terms.whnf(spec.type, problem.arity), fc.FuncType):
      continue
    try:
      residual = problem.env.reduce(Pred(DATA_CLASS, spec.type, spec))
    except NoInstance:
      continue
    for pred in residual:
      key = pred.classname, id(terms.prune(pred.term))
      if key not in seen:
        seen.add(key)
        predicates.append(pred)
  scheme, _ = problem._make_scheme(predicates)
  problem.display_scheme = scheme
  return unqualify(str(scheme))


def choice(interp, first, second, *more):
  values = (first, second, *more)
  result = values[-1]
  for value in reversed(values[:-1]):
    result = interp._prelude['?'](value, result)
  return result


def let(interp, body, bindings):
  return Term(interp, LetForm(_convert(interp, body),
      {name: _convert(interp, value) for name, value in bindings.items()}))


def parse(interp, text, imports=()):
  from ..interpreter import compile as compiler
  from ..exceptions import CompileError
  if not isinstance(text, str):
    raise TypeError('parse takes the text of a Curry expression')
  stmts, path = compiler.getImportSpecForExpr(interp, imports)
  try:
    func, names, module = compiler.compile_expression(interp, text, stmts, path)
  except CompileError as error:
    raise text_error(error, text, len(stmts), bool(names_in_text(text))) from None
  # A compiled expression keeps its module alive and its symbols typed even
  # after the expression compiler removes it from the session registry.
  variables = [Var(interp, name) for name in names]
  result = Term(interp, [func, *variables])
  result._text = text
  result._text_module = module
  result._free_vars = dict(sorted(result._free_vars.items(), key=lambda item:
      re.search(r"(?<![A-Za-z0-9_'])%s(?![A-Za-z0-9_'])" % re.escape(item[0]), text).start()))
  return result


def names_in_text(text):
  from ..typecheck.goals import split_where_free
  return split_where_free(text)[1]


def text_error(error, text, imports, lifted):
  from ..exceptions import CompileError
  # A translation failure is Sprite's complete sentence, not a front-end report.
  from ..toolchain.flat2icurry.errors import Flat2ICurryError
  if isinstance(error, Flat2ICurryError):
    return error
  # Imports and the lifted-goal declaration precede the expression.
  report = error.report
  line, column = error.line, error.column
  if line is None or column is None:
    positions = re.findall(r':(\d+):(\d+)(?:[-:].*)?', report)
    line, column = (map(int, positions[0]) if positions else (1, 1))
  prefix_lines = imports + int(lifted)
  line = max(1, line - prefix_lines)
  if line == 1:
    from ..interpreter.compile import COMPILED_NAME
    from ..typecheck.goals import split_where_free
    _, names = split_where_free(text)
    column = max(1, column - len(COMPILED_NAME) - sum(len(n) + 1 for n in names) - 3)
  message = report.split('Error:', 1)[-1].strip().splitlines()[0]
  result = CompileError('%d:%d Error: %s' % (line, column, message))
  result.report, result.line, result.column = report, line, column
  return result
