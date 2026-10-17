'''Typed Curry terms and the metadata of their names.'''

from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterator, Sequence
import re
from dataclasses import dataclass

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
    self._free_vars = named_vars(form)
    if has_refs(form):
      self._node = None
      self._signature = '?'
      self._defaulted = None
      return
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
      fix_variable_types(problem)
      self._signature = signature(problem)
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
        self._defaulted = unqualify(builder.show_type(problem.typeexpr))
        builder.record_of(interp).put(self._node, problem.scheme, problem.typeexpr)
    if symbol is not None:
      self.__doc__ = '%s :: %s' % (symbol.fullname, symbol.signature)

  free_vars = property(lambda self: dict(self._free_vars))

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
    result._free_vars = {}
    result._annotation = None
    with raw_symbols():
      result._signature = builder.typeof(self._interp, node)
      result._defaulted = builder.typeof(self._interp, node, True)
    return result

  @classmethod
  def from_symbol(cls, info, module):
    metadata = getattr(module, '.info')._symbols
    sym = metadata.get(info.name)
    if sym is None or sym._info is not info:
      sym = metadata[info.name] = Symbol(info, module)
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

  def __choice__(self, other):
    return choice(self._interp, self, other)

  def __rchoice__(self, other):
    return choice(self._interp, other, self)

  def _op(self, name, left, right):
    from ..typecheck.errors import ConversionError
    try:
      _convert(self._interp, left)
      _convert(self._interp, right)
    except ConversionError:
      return NotImplemented
    return self._interp.prelude[name](left, right)

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
  def __neg__(self): return self._interp.prelude.negate(self)

  def __infix__(self, op, other):
    return self._infix(op, other, False)

  def __rinfix__(self, op, other):
    return self._infix(op, other, True)

  def _infix(self, op, other, reflected):
    from ..typecheck.errors import ConversionError
    modules = [self._interp.prelude]
    for value in walk_forms((self, other)):
      if isinstance(value, Term) and value.symbol is not None:
        module = value.symbol.module
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

  def __str__(self):
    from .termshow import show
    return show(self)

  def __repr__(self):
    return '<Term %s :: %s>' % (self, self._signature)

  def __eq__(self, other):
    if isinstance(other, Var):
      return self is other
    return isinstance(other, Term) and _graph_key(self._node, variable_nodes(self)) == _graph_key(other._node, variable_nodes(other))

  def __hash__(self):
    return hash(_graph_key(self._node, variable_nodes(self)))

  # The old API reads symbol metadata directly until its removal task.
  def __getattr__(self, name):
    if name in ('successor', 'successors'):
      return getattr(self._node, name)
    if self.symbol is not None:
      return getattr(self.symbol._info, name)
    raise AttributeError(name)


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
  seen = {}
  key = []
  pending = [root]
  while pending:
    node = pending.pop()
    if not isinstance(node, backends.Node):
      key.append(('literal', type(node), node))
    elif variables and node.id() in variables:
      key.append(('variable', variables[node.id()]))
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
  if value is anonymous:
    return Var(interp)
  if isinstance(value, Term):
    return value
  import types
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
  def __init__(self, interp, name=None, type=None):
    from ..expressions import free
    if name is not None and not re.fullmatch(r"[a-z_][A-Za-z0-9_']*", name):
      raise ValueError('%r is not a Curry variable name' % name)
    self.name = name
    self._marker = free(exprtype=type)
    self._marker._var = self
    self._interp = interp
    self._form = self._marker
    self._args = ()
    self.symbol = None
    self._annotation = None
    self._free_vars = {} if name is None else {name: self}
    self._signature = 'Data a => a' if type is None else type
    self._defaulted = None
    if type is not None:
      from ..typecheck import builder
      with raw_symbols():
        b = builder.TypedBuilder(interp)
        builder.TypedProblem(b, b.specs((self,)))

  @property
  def _node(self):
    from ..expressions import untyped_expr
    with raw_symbols():
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
  def __init__(self, interp, name):
    self._interp = interp
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
        marker.exprtype = terms.zonk(t, arity=problem.arity)
        marker._var._signature = unqualify(problem.show(t))


def signature(problem):
  """Include Data for polymorphic free variables, as a free declaration does."""
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
  return unqualify(str(scheme))


def choice(interp, first, second, *more):
  values = (first, second, *more)
  result = values[-1]
  for value in reversed(values[:-1]):
    result = interp.prelude['?'](value, result)
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
  # Imports and the lifted-goal declaration precede the expression.
  report = str(error)
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
