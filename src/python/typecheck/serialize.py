'''
The serializer: prints the description of a Python-built expression as
Curry text (item Y8 of the typed boundary, epic #48).

A spec tree (:mod:`.engine`, :mod:`.builder`) describes the arguments of
``curry.expr``.  :func:`serialize` prints it in Curry syntax, so that the
same expression can be compiled by the front end and evaluated by the PAKCS
REPL, the oracles of the tests.  Python values are written as Curry
literals.  An operand without Curry text, a Curry node of an earlier
evaluation or an iterator, becomes a parameter.  A free marker becomes a
``let x1 free in`` declaration, or a parameter when the caller lifts the
markers as the REPL does for ``where x free``.  Anchors and references
become a recursive ``let``.  Names of the Prelude print unqualified, names
of other modules qualified, so the text compiles in a module that imports
them.

Both passes of the serializer, the naming and the printing, walk the tree
with an explicit stack, so the depth of a description does not bound the
depth of the Python stack.
'''

from .. import exceptions
from ..objects import CurryNodeInfo
from ..toolchain.flat2icurry import flatcurry as fc
from ..toolchain.flat2icurry.terms import Char, showterm
from ..utility import strings
from . import terms
from .engine import App, Free, Iter, Known, List, Lit, Spec, Tuple, Typed
from .sigtable import PRELUDE, Scheme, _is_tuple_name
import math, numbers, re

__all__ = [
    'CURRY_KEYWORDS', 'SerializeError', 'Serialized', 'curry_literal'
  , 'float_text', 'is_identifier', 'serialize', 'serialize_call'
  , 'serialize_description'
  ]

CHAR = fc.prelude('Char')
LIST = fc.prelude('[]')

# The reserved words of Curry.  A generated name never clashes with one, and
# a user's anchor name that is one is renamed.
CURRY_KEYWORDS = frozenset([
    'as', 'case', 'class', 'data', 'default', 'deriving', 'do', 'else'
  , 'external', 'fcase', 'free', 'hiding', 'if', 'import', 'in', 'infix'
  , 'infixl', 'infixr', 'instance', 'let', 'module', 'newtype', 'of'
  , 'qualified', 'then', 'type', 'where'
  ])

_IDENTIFIER = re.compile(r"^[a-z][A-Za-z0-9_']*$")

class SerializeError(ValueError):
  '''A part of the description has no Curry text, or cannot be written.'''

def is_identifier(name):
  '''
  Whether ``name`` is a Curry variable name that is no keyword.  A name that
  starts with an underscore does not count: the builder names its own
  anchors that way.
  '''
  return bool(_IDENTIFIER.match(name)) and name not in CURRY_KEYWORDS

# Literals
# ========
def float_text(value):
  '''
  A Python float as a Curry literal.  The mantissa always has a decimal
  point, the exponent has no plus sign: ``1.0e20``, ``1.5e-7``, ``2.5``.  A
  negative number is written in parentheses.  An infinity or a NaN has no
  literal.
  '''
  value = float(value)
  if math.isnan(value) or math.isinf(value):
    raise SerializeError('%r has no Curry literal' % value)
  text = repr(value)
  negative = text.startswith('-')
  if negative:
    text = text[1:]
  mantissa, e, exponent = text.partition('e')
  if '.' not in mantissa:
    mantissa += '.0'
  if e:
    exponent = exponent.lstrip('+')
    text = '%se%s' % (mantissa, exponent)
  else:
    text = mantissa
  return '(-%s)' % text if negative else text

def curry_literal(value, as_char=None):
  '''
  A Python value as a Curry literal: a bool, an int, a float, a str or
  bytes.  A one-character string is a ``Char`` when ``as_char`` is true, a
  string when it is false, and a ``Char`` by default.  Any other value, and
  ``None``, has no literal.
  '''
  if isinstance(value, bool):
    return 'True' if value else 'False'
  if isinstance(value, numbers.Integral):
    value = int(value)
    return '(%d)' % value if value < 0 else '%d' % value
  if isinstance(value, numbers.Real):
    return float_text(value)
  if isinstance(value, (str, bytes)):
    text = strings.ensure_str(value)
    if as_char is None:
      as_char = len(text) == 1
    if as_char and len(text) == 1:
      return showterm(Char(text))
    if not text:
      return '""'
    return showterm(text)
  raise SerializeError('%r has no Curry literal' % (value,))

# The result
# ==========
class Serialized:
  '''
  The Curry text of a description.

  Attributes:
    body:
        The expression without the declarations of the free markers and
        the anchors.
    params:
        The names of the operands without Curry text, in the order of
        their first occurrence: Curry nodes, iterators, and the other
        untyped parts.
    frees:
        The names of the free markers, in the order of their first
        occurrence.
    bindings:
        The anchors as pairs of a name and the text of the value, in the
        order of their first occurrence.
    exprtype:
        The type the expression was annotated with, or None.
    modules:
        The names of the modules whose symbols the text names qualified.
  '''
  def __init__(self, body, params, frees, bindings, exprtype, modules):
    self.body = body
    self.params = list(params)
    self.frees = list(frees)
    self.bindings = list(bindings)
    self.exprtype = exprtype
    self.modules = sorted(modules)

  def _let(self, body, frees):
    if self.bindings:
      decls = '; '.join('%s = %s' % (name, text) for name, text in self.bindings)
      body = 'let %s in %s' % (decls, body)
    if frees:
      body = 'let %s free in %s' % (', '.join(frees), body)
    return body

  @property
  def text(self):
    '''
    The expression as Curry text: the free markers declared with ``let x1
    free in``, the anchors bound by a recursive ``let``.  The parameters,
    if any, are free names of the text; see :meth:`definition`.
    '''
    return self._let(self.body, self.frees)

  def expression(self, lift_frees=False):
    '''
    The text of the expression.  With ``lift_frees`` the free markers are
    not declared: they are parameters, as the REPL of PAKCS makes them for
    ``where x free``.
    '''
    return self._let(self.body, () if lift_frees else self.frees)

  def parameters(self, lift_frees=True):
    '''The names of the parameters of :meth:`definition`.'''
    return self.params + (self.frees if lift_frees else [])

  def definition(self, name='compiled_expression', lift_frees=True):
    '''
    A Curry function definition of the expression: ``name p1 x1 = body``,
    whose parameters are the operands without text and, with
    ``lift_frees``, the free markers.
    '''
    params = self.parameters(lift_frees)
    head = ' '.join([name] + params)
    return '%s = %s' % (head, self.expression(lift_frees))

  def where_text(self):
    '''
    The expression with a trailing ``where x1, x2 free`` clause instead of
    the ``let``: the form the text route lifts to parameters.  The
    description may have no operand without text.
    '''
    if self.params:
      raise SerializeError(
          'the description has operands without Curry text: %s'
              % ', '.join(self.params)
        )
    text = self.expression(lift_frees=True)
    if self.frees:
      text = '%s where %s free' % (text, ', '.join(self.frees))
    return text

  def __str__(self):
    return self.text

  def __repr__(self):
    return '<Serialized %s>' % self.text

# The serializer
# ==============
def _is_operator(name):
  return bool(name) and not (name[0].isalnum() or name[0] == '_')

def _app_name(app):
  '''The name and the module of the symbol of an application.'''
  symbol = app.symbol
  if isinstance(symbol, CurryNodeInfo):
    icur = symbol.icurry
    if icur is not None:
      return icur.name, icur.modulename
    return symbol.name, symbol.info.name.rpartition('.')[0]
  if isinstance(symbol, Scheme):
    return symbol.name, symbol.modulename
  modulename, _, name = str(symbol).rpartition('.')
  return name, modulename

def _builder_specs():
  '''The spec classes of the builder; imported on first use.'''
  from . import builder
  return builder

class _Names:
  '''Generates the names of the parameters, markers and anchors.'''
  def __init__(self, reserved):
    self.used = set(reserved) | CURRY_KEYWORDS

  def fresh(self, prefix):
    i = 1
    while True:
      name = '%s%d' % (prefix, i)
      if name not in self.used:
        self.used.add(name)
        return name
      i += 1

  def keep(self, name):
    '''Keeps a user's name when it is a free identifier; else None.'''
    if name is None or not is_identifier(name) or name in self.used:
      return None
    self.used.add(name)
    return name

class _Serializer:
  '''
  Prints one spec tree.  The first pass names the parameters, the free
  markers and the anchors in the order of their first occurrence; the
  second pass emits the tokens of the text.  Both walk with an explicit
  stack.
  '''
  def __init__(self, module=None, anchor_names=None):
    self.module = module
    self.anchor_names = {} if anchor_names is None else dict(anchor_names)
    self.params = []       # (name, spec)
    self.frees = []        # names in order
    self.anchors = []      # (var, name, child spec)
    self.modules = set()
    self._param_of = {}    # id(spec) -> name
    self._free_of = {}     # key of a marker -> name
    self._anchor_of = {}   # var -> name

  # Pass 1: names
  # -------------
  def name(self, root):
    B = _builder_specs()
    stack = [root]
    symbols = set()
    specs = []
    while stack:
      spec = stack.pop()
      specs.append(spec)
      if isinstance(spec, App):
        name, modulename = _app_name(spec)
        symbols.add(name)
        if modulename != PRELUDE and modulename != self.module:
          self.modules.add(modulename)
      stack.extend(reversed(_children(spec, B)))
    names = _Names(symbols)
    for spec in specs:
      if isinstance(spec, Free):
        key = id(spec) if spec.payload is None else id(spec.payload)
        if key not in self._free_of:
          self._free_of[key] = names.fresh('x')
          self.frees.append(self._free_of[key])
      elif isinstance(spec, B.Wrap) and spec.kind == 'anchor':
        var = spec.extra
        if var not in self._anchor_of:
          name = names.keep(self.anchor_names.get(var)) or names.fresh('a')
          self._anchor_of[var] = name
          self.anchors.append((var, name, spec.items[0]))
      elif self._is_param(spec, B):
        key = _param_key(spec)
        if key not in self._param_of:
          name = names.fresh('p')
          self._param_of[key] = name
          self.params.append((name, spec))

  @staticmethod
  def _is_param(spec, B):
    if isinstance(spec, (Known, Iter)):
      return True
    if isinstance(spec, B.Raw):
      return _raw_literal(spec, B) is None
    return False

  # Pass 2: tokens
  # --------------
  def emit(self, root):
    '''The text of a spec.'''
    B = _builder_specs()
    out = []
    stack = [(root, 0)]
    while stack:
      item = stack.pop()
      if isinstance(item, str):
        out.append(item)
        continue
      spec, prec = item
      stack.extend(reversed(self.pieces(spec, prec, B)))
    return ''.join(out)

  def pieces(self, spec, prec, B):
    '''The tokens of a spec: strings and pairs of a child and its precedence.'''
    if isinstance(spec, App):
      return self._app_pieces(spec, prec)
    if isinstance(spec, Lit):
      return [self._literal(spec)]
    if isinstance(spec, Free):
      key = id(spec) if spec.payload is None else id(spec.payload)
      return [self._free_of[key]]
    if isinstance(spec, List):
      return _sequence('[', spec.items, ']')
    if isinstance(spec, Tuple):
      if not spec.items:
        return ['()']
      if len(spec.items) == 1:
        raise SerializeError('Curry has no 1-tuple')
      return _sequence('(', spec.items, ')')
    if isinstance(spec, Typed):
      text = spec.text if isinstance(spec.text, str) else _type_text(spec.text)
      return ['(', (spec.spec, 0), ' :: ', text, ')']
    if isinstance(spec, (Known, Iter)):
      return [self._param_of[_param_key(spec)]]
    if isinstance(spec, B.Raw):
      text = _raw_literal(spec, B)
      return [self._param_of[_param_key(spec)] if text is None else text]
    if isinstance(spec, B.Wrap):
      if spec.kind == 'anchor':
        return [self._anchor_of[spec.extra]]
      if spec.kind == 'fwd':
        return [(spec.items[0], prec)]
      raise SerializeError('a %s node has no Curry text' % spec.kind)
    if isinstance(spec, B.Ref):
      return [self._anchor_of[spec.payload]]
    if isinstance(spec, B.Unboxed):
      return [curry_literal(spec.payload)]
    if isinstance(spec, B.Group):
      return [(spec.items[-1], prec)]
    raise SerializeError('cannot serialize %r' % (spec,))

  def _app_pieces(self, app, prec):
    name, modulename = _app_name(app)
    args = app.args
    qualified = modulename not in (PRELUDE, self.module)
    if modulename == PRELUDE:
      if name == '[]' and not args:
        return ['[]']
      if name == '()' and not args:
        return ['()']
      if _is_tuple_name(name) and len(args) == len(name) - 1:
        return _sequence('(', args, ')')
    shown = '%s.%s' % (modulename, name) if qualified else name
    if modulename == PRELUDE and (_is_tuple_name(name) or name in ('[]', '()')):
      # A special constructor in prefix position: (,) 1, (:) 1.
      head = shown
    elif _is_operator(name):
      if len(args) == 2:
        pieces = [(args[0], 1), ' %s ' % shown, (args[1], 1)]
        return ['('] + pieces + [')'] if prec > 0 else pieces
      head = '(%s)' % shown
    else:
      head = shown
    if not args:
      return [head]
    pieces = [head]
    for arg in args:
      pieces.append(' ')
      pieces.append((arg, 2))
    return ['('] + pieces + [')'] if prec > 1 else pieces

  def _literal(self, lit):
    value = lit.value
    if value is None:
      raise SerializeError('None has no Curry text')
    as_char = None
    if isinstance(value, (str, bytes)) and lit.type is not None:
      t = terms.whnf(lit.type)
      if isinstance(t, fc.TCons):
        as_char = t.name == CHAR
    return curry_literal(value, as_char)

def _sequence(open_, items, close):
  pieces = [open_]
  for i, item in enumerate(items):
    if i:
      pieces.append(', ')
    pieces.append((item, 0))
  pieces.append(close)
  return pieces

def _children(spec, B):
  if isinstance(spec, App):
    return spec.args
  if isinstance(spec, (List, Tuple, B.Wrap, B.Group)):
    return spec.items
  if isinstance(spec, Typed):
    return [spec.spec]
  return ()

def _param_key(spec):
  '''
  The key of a parameter: the identity of its value, so that one Curry node
  or one iterator given twice is one parameter; else the spec itself.
  '''
  payload = spec.payload
  if isinstance(payload, (list, tuple)) or payload is None:
    return ('spec', id(spec))
  node_id = getattr(payload, 'id', None)
  if callable(node_id):
    return ('node', node_id())
  return ('value', id(payload))

def _raw_literal(spec, B):
  '''
  The text of an untyped part that has one: the failure marker, and a
  boxed literal over its unboxed payload, ``[Int, unboxed(3)]``, written
  with the type the form fixes: ``(3 :: Int)``.  None for a Curry node, a
  dictionary and any other part.
  '''
  from .. import expressions
  payload = spec.payload
  if spec.walk:
    return None
  if payload is expressions.fail:
    return 'failed'
  if isinstance(payload, list) and len(payload) == 2 \
      and isinstance(payload[1], expressions.unboxed) \
      and spec.typeexpr is not None:
    return '(%s :: %s)' % (
        curry_literal(payload[1].value), _type_text(spec.typeexpr)
      )
  return None

# The entry points
# ================
def serialize(spec, exprtype=None, module=None, anchor_names=None):
  '''
  Prints a spec tree as Curry text.

  Args:
    spec:
        The root of the tree: a spec of the engine or of the builder, or a
        :class:`Description <curry.typecheck.builder.Description>`.
    exprtype:
        The type of the expression in Curry syntax, or None.  The body is
        annotated with it: ``(body :: T)``.
    module:
        The name of the module whose symbols print unqualified, besides the
        Prelude; the module the text is compiled in.
    anchor_names:
        A dict from the type variable of an anchor to its name, as the
        builder keeps it (``TypedBuilder.anchor_vars`` inverted).  A name
        that is a free Curry identifier is kept.

  Returns:
    A :class:`Serialized`.

  Raises:
    SerializeError:
        A part of the tree has no Curry text and cannot be a parameter:
        ``None``, a set guard, a constraint, a 1-tuple, a float without a
        literal.
  '''
  B = _builder_specs()
  if isinstance(spec, B.Description):
    if anchor_names is None:
      anchor_names = {
          var: name for name, var in spec.builder.anchor_vars.items()
        }
    spec = spec.root
  if not isinstance(spec, Spec):
    raise TypeError('expected a spec or a description, got %r' % (spec,))
  s = _Serializer(module, anchor_names)
  s.name(spec)
  body = s.emit(spec)
  if exprtype is not None:
    text = exprtype if isinstance(exprtype, str) else _type_text(exprtype)
    body = '(%s :: %s)' % (body, text)
  bindings = [(name, s.emit(child)) for _, name, child in s.anchors]
  params = [name for name, _ in s.params]
  return Serialized(body, params, s.frees, bindings, exprtype, s.modules)

def _type_text(typeexpr):
  from .sigtable import show_type
  return show_type(typeexpr)

def serialize_call(
    interp, args, anchors=None, exprtype=None, module=None, typed=True
  ):
  '''
  Prints the arguments of ``curry.expr`` as Curry text.  ``args`` are the
  positional arguments, ``anchors`` the keyword anchors as a dict.  With
  ``typed`` the tree is typed first (phase 1 of the engine), so that a
  one-character string under ``[Char]`` prints as a string; a typing
  failure leaves the tree untyped, and the text follows the Python types.
  '''
  B = _builder_specs()
  builder = B.TypedBuilder(interp)
  root = builder.specs(tuple(args), anchors or {})
  if typed:
    try:
      B.TypedProblem(builder, root, exprtype)
    except exceptions.CurryTypeError:
      pass
  names = {var: name for name, var in builder.anchor_vars.items()}
  return serialize(root, exprtype=exprtype, module=module, anchor_names=names)

def serialize_description(description, exprtype=None, module=None, typed=True):
  '''Prints a :class:`Description <curry.typecheck.builder.Description>`.'''
  B = _builder_specs()
  if typed:
    try:
      B.TypedProblem(description.builder, description.root, exprtype)
    except exceptions.CurryTypeError:
      pass
  return serialize(description, exprtype=exprtype, module=module)
