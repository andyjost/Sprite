'''
The typed builder of ``curry.expr`` (item Y7 of the typed boundary, epic
#48).

``curry.expr`` describes its arguments as a tree of specs, types the tree
with the engine (:mod:`.engine`), defaults the class constraints, resolves
the dictionaries, and then builds the nodes through ``make_node`` of the
backend.  The conversion of the arguments, the typing and the
materialization each walk the tree with an explicit stack, so the depth of
a description is not bounded by the recursion limit.  Python values convert
by the expected type: an ``int`` under ``Float`` is a ``Float``, a ``str``
under ``[Char]`` is one string, a list converts in a loop under its element
type, and the items of an iterator convert when the list is demanded.  A
Curry node that fills a parameter is typed by a walk of its content, capped
at :data:`VALUE_WALK_CAP` nodes; a bare node alone passes through untouched.
The walk types a node without successors, such as ``[]``, at every position
it holds, because the runtime shares one such node between positions of
different types (:meth:`TypedProblem._walk`).

The result type of a node the builder returns is kept in a weak record
(:class:`TypeRecord`) keyed by the identity of the node, so ``curry.typeof``
answers for it and ``curry.eval`` hands the static type of a goal to the
converter.  :class:`Description` holds a tree of specs for the DSL and types
it only when a consumer asks for nodes.
'''

from .. import backends, exceptions, inspect
from ..common import T_FUNC
from ..objects import CurryNodeInfo
from ..objects.handle import getHandle
from ..toolchain.flat2icurry import flatcurry as fc
from ..utility import strings
from . import engine, errors, terms
from .engine import (
    App, Free, Iter, Known, List, Lit, Problem, Spec, Tuple, Typed, describe
  )
from .instances import DATA_CLASS
from .sigtable import INST_PREFIX, Scheme, show_type
from .terms import Rigid, Var, tcons, whnf
import collections.abc, itertools, numbers, weakref

__all__ = [
    'Description', 'Group', 'Raw', 'Ref', 'TypeRecord', 'TypedBuilder'
  , 'TypedProblem', 'Unboxed', 'VALUE_WALK_CAP', 'Wrap', 'build'
  , 'build_description', 'record_of', 'recorded', 'result_type', 'symbol_map'
  , 'typeof'
  ]

# The number of nodes the walk that types a Curry value visits before it
# stops with ValueTooLargeError; curry.typed(node, 'T') states the type
# instead.
VALUE_WALK_CAP = 100000

BOOL, INT, FLOAT, CHAR = (fc.prelude(n) for n in ('Bool', 'Int', 'Float', 'Char'))
LIST = fc.prelude('[]')
STRING_NODE = '_biString'
GENERATOR_NODE = '_biGenerator'

# The specs of the builder
# ========================
# The engine knows App, Lit, Free, Known, List, Tuple, Iter and Typed.  The
# builder adds the forms of curry.expr that have no type of their own.
class Raw(Spec):
  '''
  A part the typed builder makes untyped.  With ``walk`` set, the payload is
  a Curry node typed by a walk of its content.  Otherwise the payload is
  built by the untyped builder: the ``fail`` marker, a list headed by an
  InfoTable, the application of a class dictionary (an ``_inst#`` symbol),
  or a boxed literal over an unboxed value; its type is ``typeexpr`` when
  given, else a fresh variable.
  '''
  __slots__ = ('walk', 'typeexpr')

  def __init__(self, payload, walk=False, typeexpr=None):
    Spec.__init__(self, payload)
    self.walk = walk
    self.typeexpr = typeexpr

  def __repr__(self):
    return '<value>'

class Wrap(Spec):
  '''
  A node around one typed child.  The kinds: ``anchor`` (``extra`` is the
  variable of the anchor, shared with its references), ``fwd``, ``setgrd``
  (``extra`` is the set id), ``strict``, ``nonstrict`` and ``binding``
  (``extra`` is the pair, built untyped).
  '''
  __slots__ = ('kind', 'items', 'extra')

  def __init__(self, kind, extra=None):
    Spec.__init__(self)
    self.kind = kind
    self.items = [None]
    self.extra = extra

  def __repr__(self):
    return describe(self.items[0])

class Ref(Spec):
  '''A reference to an anchor; ``payload`` is the variable of the anchor.'''
  __slots__ = ()

  def __init__(self, var):
    Spec.__init__(self, var)

  def __repr__(self):
    return '<ref>'

class Unboxed(Spec):
  '''
  An :class:`unboxed <curry.expressions.unboxed>` marker the problem
  refuses; ``payload`` is the Python value.  The payload of a primitive,
  ``[Int, unboxed(3)]``, is a :class:`Raw` part instead
  (:meth:`TypedBuilder._application`), so this spec stands alone, in a list
  or a tuple, or as an argument, where a node is expected (issue #107); or,
  with ``primitive`` set to ``'Int'``, ``'Char'`` or ``'Float'``, it is a
  payload that does not fit that primitive, such as ``[Int, unboxed(2.5)]``.
  A description prints the payload.
  '''
  __slots__ = ('primitive',)

  def __init__(self, payload, primitive=None):
    Spec.__init__(self, payload)
    self.primitive = primitive

  def __repr__(self):
    return repr(self.payload)

class Group(Spec):
  '''
  The anchors of the keyword arguments followed by the expression.  The
  type and the node of the group are those of the last item; the anchors
  are built first, so a reference to one of them finds its node.
  '''
  __slots__ = ('items',)

  def __init__(self):
    Spec.__init__(self)
    self.items = []

  def __repr__(self):
    return describe(self.items[-1])

def _app(symbol, nargs):
  app = App(symbol)
  app.args = [None] * nargs
  return app

def _list(n):
  spec = List([])
  spec.items = [None] * n
  return spec

def _tuple(n):
  spec = Tuple([])
  spec.items = [None] * n
  return spec

def _typed(text):
  spec = Typed(Lit(0), text)
  spec.spec = None
  return spec

def _children(spec):
  if isinstance(spec, App):
    return spec.args
  if isinstance(spec, (List, Tuple, Wrap, Group)):
    return spec.items
  if isinstance(spec, Typed):
    return [spec.spec]
  return ()

def _place(container, index, spec):
  if isinstance(container, list):
    container[index] = spec
  else:
    setattr(container, index, spec)

def _follow(node):
  while inspect.isa_fwd(node):
    node = node.successor(0)
  return node

def _partial_parts(node):
  '''
  The info table of the head of a partial application and the arguments it
  holds.  On the Python backend the node holds the count of the missing
  arguments and the term of the head; on the C++ backend it holds the
  count, the head (``Node.partial_head``) and the arguments.
  '''
  successors = list(node.successors)
  if len(successors) == 2 and isinstance(successors[1], backends.Node):
    term = successors[1]
    return term.info, list(term.successors)
  head = getattr(node, 'partial_head', None)
  return head, successors[2:]

def _symbol_name(symbol):
  '''
  The name of a symbol from its ICurry object.  The info table of the
  backend holds the name too, but the C++ backend has a latent defect: after
  a reset that unloaded modules, the name of a Prelude symbol can be read
  through a dangling pointer (see tests/unit_typed_expr.py,
  TestForms.test_symbol_names).
  '''
  icur = symbol.icurry
  return symbol.name if icur is None else icur.name

# The symbol of an info table
# ===========================
def symbol_map(interp):
  '''
  A dict from the id of an info table to its symbol, over the loaded
  modules of an interpreter.  The map is built again when a module was
  loaded or released since the last call.
  '''
  names = tuple((name, id(module)) for name, module in interp.modules.items())
  cache = getattr(interp, '_info_symbols', None)
  if cache is None or cache[0] != names:
    table = {}
    for module in list(interp.modules.values()):
      for mod in getHandle(module).itermodules():
        symbols = getattr(mod, '.symbols', None)
        if symbols:
          for symbol in symbols.values():
            table[id(symbol.info)] = symbol
    cache = interp._info_symbols = (names, table)
  return cache[1]

# The record of result types
# ==========================
class TypeRecord:
  '''
  The result types of the nodes ``curry.expr`` returned: the undefaulted
  scheme and the defaulted type.  An entry is keyed by the identity of the
  node and held by a weak reference, so it goes when the node goes and is
  never lent to a node that took the same id later.
  '''
  def __init__(self):
    self._entries = {}

  def put(self, node, scheme, typeexpr):
    key = node.id()
    entries = self._entries
    def forget(ref, key=key, entries=entries):
      entry = entries.get(key)
      if entry is not None and entry[0] is ref:
        del entries[key]
    try:
      ref = weakref.ref(node, forget)
    except TypeError:
      return
    entries[key] = (ref, scheme, typeexpr)

  def get(self, node):
    '''The pair of the scheme and the type of a recorded node, or None.'''
    entry = self._entries.get(node.id())
    if entry is None or entry[0]() is not node:
      return None
    return entry[1], entry[2]

  def __len__(self):
    return len(self._entries)

def record_of(interp):
  record = getattr(interp, '_typed_results', None)
  if record is None:
    record = interp._typed_results = TypeRecord()
  return record

def recorded(interp, node):
  '''The recorded scheme and type of a node, or None.'''
  return record_of(interp).get(node)

def result_type(interp, node):
  '''The defaulted result type of a node ``curry.expr`` built, or None.'''
  if not isinstance(node, backends.Node):
    return None
  entry = record_of(interp).get(node)
  return None if entry is None else entry[1]

# The builder
# ===========
class TypedBuilder:
  '''
  Builds one expression: converts the arguments of ``curry.expr`` to specs
  (:meth:`specs`), types them (:class:`TypedProblem`) and makes the nodes
  (:meth:`materialize`).
  '''
  def __init__(self, interp, target=None):
    from .. import expressions
    self.X = expressions
    self.interp = interp
    self.target = target
    self.prelude = interp.prelude
    self.fsyms = interp.backend.fundamental_symbols
    self._mknode = interp.backend.make_node
    self.cxx = interp.flags['backend'] == 'cxx'
    self.counter = itertools.count(1)
    self.anchor_vars = {}  # name -> the key of the anchor
    self.anchors = {}      # the key -> its node, None until built
    self._declared = set() # the keyword anchors not yet converted
    self.brokenrefs = {}
    self._raw = None
    self._dicts = {}

  # The untyped builder, for the parts without a type.
  @property
  def raw(self):
    if self._raw is None:
      self._raw = self.X.ExpressionBuilder(self.interp, raw=False)
    return self._raw

  def raw_build(self, form, target=None):
    builder = self.raw
    builder.target = target
    try:
      if isinstance(form, list):
        return builder(*form)
      return builder(form)
    finally:
      builder.target = None

  # Specs
  # -----
  def specs(self, args, anchors=()):
    '''
    The spec tree of the arguments of ``curry.expr``.  ``anchors`` are the
    keyword arguments, pairs of a name and a value; they come first in a
    :class:`Group`.
    '''
    X = self.X
    anchors = dict(anchors)
    # Every keyword anchor is declared before any value is converted, so
    # that an anchor may refer to one that comes later.
    for name in anchors:
      self._declare_anchor(name)
    forms = [X.anchor(value, name=name) for name, value in anchors.items()]
    forms.append(self._form(args))
    items = [None] * len(forms)
    stack = [(form, items, i) for i, form in reversed(list(enumerate(forms)))]
    while stack:
      value, container, index = stack.pop()
      spec, children = self.spec_of(value)
      _place(container, index, spec)
      stack.extend(reversed(children))
    if len(items) == 1:
      return items[0]
    group = Group()
    group.items = items
    return group

  def _form(self, args):
    '''One Python value for the positional arguments of ``curry.expr``.'''
    if len(args) == 1:
      return args[0]
    if not args:
      raise exceptions.CurryTypeError('curry.expr takes an expression; none given')
    head = args[0]
    if isinstance(head, (CurryNodeInfo, backends.InfoTable)):
      return list(args)
    raise exceptions.CurryTypeError('invalid arguments after %r' % (head,))

  def spec_of(self, arg):
    '''
    The spec of one argument and the children to convert, as triples of a
    value, a container and an index.
    '''
    X = self.X
    if hasattr(arg, 'rvalue'):
      arg = arg.rvalue
    if isinstance(arg, Spec):
      return arg, ()
    if isinstance(arg, Description):
      # The anchors of the description join this build, by their keys; the
      # names stay with the description.
      for key in arg.builder.anchors:
        self.anchors.setdefault(key, None)
      if arg.exprtype is None:
        return arg.root, ()
      annotated = _typed(arg.exprtype)
      annotated.spec = arg.root
      return annotated, ()
    if isinstance(arg, (str, bytes)):
      return Lit(strings.ensure_str(arg)), ()
    if arg is None or isinstance(arg, (bool, numbers.Real)):
      return Lit(arg), ()
    if isinstance(arg, CurryNodeInfo):
      return self._application(arg, ())
    if isinstance(arg, list):
      if arg:
        head = arg[0]
        if isinstance(head, CurryNodeInfo):
          return self._application(head, arg[1:])
        if isinstance(head, backends.InfoTable):
          return Raw(list(arg)), ()
      spec = _list(len(arg))
      return spec, [(item, spec.items, i) for i, item in enumerate(arg)]
    if isinstance(arg, tuple):
      spec = _tuple(len(arg))
      return spec, [(item, spec.items, i) for i, item in enumerate(arg)]
    if isinstance(arg, backends.Node):
      return Raw(arg, walk=True), ()
    if isinstance(arg, X.free):
      spec = Free(arg)
      if arg.exprtype is None:
        return spec, ()
      annotated = _typed(arg.exprtype)
      annotated.spec = spec
      return annotated, ()
    if isinstance(arg, X.choice):
      return self._application(getattr(self.prelude, '?'), [arg.lhs, arg.rhs])
    if isinstance(arg, X.typed):
      spec = _typed(arg.exprtype)
      return spec, [(arg.value, spec, 'spec')]
    if isinstance(arg, X.anchor):
      spec = Wrap('anchor', self._anchor_var(arg.name))
      return spec, [(arg.value, spec.items, 0)]
    if isinstance(arg, X.ref):
      return Ref(self._ref_var(arg.name)), ()
    if isinstance(arg, X.cons):
      return self._application(self.prelude.Cons, [arg.head, arg.tail])
    if arg is X.nil:
      return self._application(self.prelude.Nil, ())
    if arg is X.fail:
      return Raw(arg), ()
    if isinstance(arg, X.fwd):
      spec = Wrap('fwd')
      return spec, [(arg.value, spec.items, 0)]
    if isinstance(arg, X._setgrd):
      spec = Wrap('setgrd', arg.sid)
      return spec, [(arg.value, spec.items, 0)]
    if isinstance(arg, X._strictconstr):
      spec = Wrap('strict', arg.pair)
      return spec, [(arg.value, spec.items, 0)]
    if isinstance(arg, X._nonstrictconstr):
      spec = Wrap('nonstrict', arg.pair)
      return spec, [(arg.value, spec.items, 0)]
    if isinstance(arg, X._valuebinding):
      spec = Wrap('binding', arg.pair)
      return spec, [(arg.value, spec.items, 0)]
    if isinstance(arg, X.unboxed):
      return Unboxed(arg.value), ()
    if isinstance(arg, collections.abc.Iterator):
      return Iter(arg), ()
    raise exceptions.CurryTypeError(
        'cannot build a Curry expression from type %r' % type(arg).__name__
      )

  def _application(self, symbol, args):
    '''
    The spec of a symbol applied to arguments.  A class dictionary (an
    ``_inst#`` symbol) is built untyped.  Dictionaries given explicitly
    before the value arguments fill the dictionary parameters of the
    symbol; the typing then takes the scheme without its context.
    '''
    args = list(args)
    if _symbol_name(symbol).startswith(INST_PREFIX):
      return Raw([symbol] + args), ()
    info = symbol.info
    if info.is_primitive and len(args) == 1 and isinstance(args[0], self.X.unboxed):
      # A boxed literal over its unboxed payload, [Int, unboxed(3)].  A
      # payload that does not fit the primitive is refused at its position.
      typename = self.X.primitive_name(info)
      if not self.X.unboxed_fits(typename, args[0].value):
        return Unboxed(args[0].value, typename), ()
      return Raw([symbol] + args, typeexpr=tcons(typename)), ()
    scheme = symbol.scheme
    if scheme is None and not args:
      # A symbol without a scheme, alone: the goal of a module without a
      # FlatCurry interface, such as a module loaded from a saved file.  It
      # is built untyped, as before the typed boundary.  With arguments the
      # engine raises the error that names the module and raw_expr.
      return Raw([symbol]), ()
    if scheme is not None and scheme.ndicts and args and self.is_dictionary(args[0]):
      n = scheme.ndicts
      if len(args) < n or not all(self.is_dictionary(a) for a in args[:n]):
        raise exceptions.CurryTypeError(
            '%s :: %s takes %d class %s before its value parameters; pass '
            'all of them or none'
                % (scheme.fullname, scheme, n, 'dictionary' if n == 1 else 'dictionaries')
          )
      explicit, args = args[:n], args[n:]
      stripped = Scheme(
          scheme.modulename, scheme.name, scheme.typevars, (), scheme.typeexpr
        , scheme.arity, 0, scheme.flat_typeexpr, scheme.is_constructor
        )
      app = _app(stripped, len(args))
      app.payload = (symbol, tuple(explicit))
    else:
      app = _app(symbol, len(args))
    return app, [(arg, app.args, i) for i, arg in enumerate(args)]

  @staticmethod
  def is_dictionary(arg):
    '''
    Whether an argument is a class dictionary: the symbol of an instance
    function, a node of one, or a list that starts with one.
    '''
    if isinstance(arg, list):
      return bool(arg) and TypedBuilder.is_dictionary(arg[0])
    if isinstance(arg, CurryNodeInfo):
      return _symbol_name(arg).startswith(INST_PREFIX)
    if isinstance(arg, backends.Node):
      info = arg.info
      if info.name.startswith(INST_PREFIX):
        return True
      # A partial application prints its head; it is a small node.
      return bool(info.is_partial) and str(arg).lstrip('(').startswith(INST_PREFIX)
    return False

  def _declare_anchor(self, name):
    '''Registers the key of a keyword anchor before its value is converted.'''
    if name in self.anchor_vars:
      raise ValueError('multiple definitions of anchor %r' % name)
    key = self.anchor_vars[name] = Var()
    self.anchors[key] = None
    self._declared.add(name)
    return key

  def _anchor_var(self, name):
    '''
    The key of an anchor: an object shared by the anchor and its references.
    The problem gives each key a type variable of its own
    (:meth:`TypedProblem.anchor_type`), so a description typed twice starts
    afresh.
    '''
    if name is None:
      while True:
        name = '_%s' % next(self.counter)
        if name not in self.anchor_vars:
          break
    elif name in self._declared:
      self._declared.discard(name)
      return self.anchor_vars[name]
    elif name in self.anchor_vars:
      raise ValueError('multiple definitions of anchor %r' % name)
    key = self.anchor_vars[name] = Var()
    self.anchors[key] = None
    return key

  def _ref_var(self, name):
    if name is None:
      if len(self.anchor_vars) != 1:
        raise ValueError(
            "invalid use of unqualified 'ref' with %s anchors defined"
                % len(self.anchor_vars)
          )
      name = next(iter(self.anchor_vars))
    var = self.anchor_vars.get(name)
    if var is None:
      raise ValueError('reference to the undefined anchor %r' % name)
    return var

  # Typing and building
  # -------------------
  def run(self, root, exprtype=None):
    '''Types a spec tree, builds its node and records the result type.'''
    problem = TypedProblem(self, root, exprtype)
    problem.solve()
    node = self.materialize(problem)
    if isinstance(node, backends.Node):
      record_of(self.interp).put(node, problem.scheme, problem.typeexpr)
    return node

  def materialize(self, problem):
    '''The node of a solved problem: a post-order walk with an explicit stack.'''
    root = problem.root
    main = root.items[-1] if isinstance(root, Group) else root
    nodes = {}
    stack = [(root, False)]
    while stack:
      spec, ready = stack.pop()
      children = _children(spec)
      if ready:
        args = [nodes[id(child)] for child in children]
        target = self.target if spec is main else None
        nodes[id(spec)] = self.finish(problem, spec, args, target)
        continue
      stack.append((spec, True))
      for child in reversed(children):
        if id(child) not in nodes:
          stack.append((child, False))
    node = nodes[id(root)]
    return self.X.fix_references(node, self.brokenrefs, self.anchors)

  def finish(self, problem, spec, args, target):
    '''The node of a spec whose children are the nodes ``args``.'''
    make = self._mknode
    if isinstance(spec, App):
      return self._app_node(problem, spec, args, target)
    if isinstance(spec, Lit):
      return self._literal_node(problem, spec, target)
    if isinstance(spec, List):
      if not args:
        return make(self.prelude.Nil, target=target)
      node = make(self.prelude.Nil)
      cons = self.prelude.Cons
      for item in reversed(args[1:]):
        node = make(cons, item, node)
      return make(cons, args[0], node, target=target)
    if isinstance(spec, Tuple):
      n = len(args)
      name = 'Prelude.()' if n == 0 else 'Prelude.(%s)' % (',' * (n - 1))
      return make(self.interp.symbol(name), *args, target=target)
    if isinstance(spec, Free):
      return self._forward(self._free_node(problem, spec), target)
    if isinstance(spec, Iter):
      return self._iterator_node(problem, spec, target)
    if isinstance(spec, Typed):
      return self._forward(args[0], target)
    if isinstance(spec, Known):
      return self._forward(spec.payload, target)
    if isinstance(spec, Raw):
      if spec.walk:
        return self._forward(spec.payload, target)
      return self.raw_build(spec.payload, target)
    if isinstance(spec, Wrap):
      return self._wrap_node(spec, args[0], target)
    if isinstance(spec, Ref):
      node = self.anchors[spec.payload]
      if node is None:
        # The anchor is built later: a placeholder that fix_references
        # replaces.  It must be a fresh node that can be forwarded.
        node = make(self.fsyms.Fwd, make(self.fsyms.Failure))
        self.brokenrefs[node.id()] = spec.payload
      return self._forward(node, target)
    if isinstance(spec, Group):
      return args[-1]
    raise TypeError('not a spec: %r' % (spec,))

  def _forward(self, node, target):
    if target is None:
      return node
    return self._mknode(self.fsyms.Fwd, node, target=target)

  def _app_node(self, problem, app, args, target):
    make = self._mknode
    if isinstance(app.payload, tuple):
      symbol, explicit = app.payload
      dicts = [self.raw_build(d) for d in explicit]
    else:
      symbol = app.symbol
      if not isinstance(symbol, CurryNodeInfo):
        symbol = self.interp.symbol(app.scheme.fullname)
      dicts = [self.dict_node(d) for d in app.dicts]
    apply_ = self.prelude.apply
    if app.erased:
      # A newtype constructor is erased by the ICurry translation: C e is e
      # and a bare C is the identity.
      if not args:
        return make(self.prelude.id, partial_info=self.fsyms.PartApplic, target=target)
      node, rest = args[0], args[1:]
      if not rest:
        return self._forward(node, target)
    else:
      direct = dicts + args
      n = symbol.info.arity
      head, rest = direct[:n], direct[n:]
      partial = self.fsyms.PartApplic if len(head) < n else None
      node = make(
          symbol, *head, partial_info=partial
        , target=target if not rest else None
        )
    for i, extra in enumerate(rest):
      node = make(
          apply_, node, extra, target=target if i == len(rest) - 1 else None
        )
    return node

  def dict_node(self, d):
    '''
    The node of a dictionary term: the instance function applied to the
    dictionaries of its context, a partial application with one missing
    argument.  One node per distinct term within one expression.
    '''
    node = self._dicts.get(d)
    if node is None:
      symbol = self.interp.symbol(d.fullname)
      args = [self.dict_node(a) for a in d.args]
      node = self._dicts[d] = self._mknode(
          symbol, *args, partial_info=self.fsyms.PartApplic
        )
    return node

  def _literal_node(self, problem, lit, target):
    make = self._mknode
    prelude = self.prelude
    t = whnf(lit.type, problem.arity)
    value = lit.value
    name = t.name if isinstance(t, fc.TCons) else None
    if name == BOOL:
      return make(prelude.True_ if value else prelude.False_, target=target)
    if name == INT:
      return make(prelude.Int, int(value), target=target)
    if name == FLOAT:
      return make(prelude.Float, float(value), target=target)
    if name == CHAR:
      return make(prelude.Char, value, target=target)
    if name == LIST:
      return self.string_node(value, target)
    # A type with a Num or a Fractional instance of its own: the literal
    # goes through the conversion method of the class, as compiled code
    # does in a polymorphic context.
    dictionary = problem.literal_dictionary(lit)
    if dictionary is not None and isinstance(value, numbers.Integral):
      method = make(prelude.fromInt, self.dict_node(dictionary))
      return make(prelude.apply, method, make(prelude.Int, int(value)), target=target)
    if dictionary is not None and isinstance(value, numbers.Real):
      method = make(prelude.fromFloat, self.dict_node(dictionary))
      return make(prelude.apply, method, make(prelude.Float, float(value)), target=target)
    raise exceptions.CurryTypeError(
        'cannot build the literal %r at type %s' % (value, problem.show(lit.type))
      )

  def string_node(self, text, target=None):
    '''
    The node of a Python string at the type ``[Char]``: on the Python
    backend one ``_biString`` node over the code points, which the step
    unfolds one character at a time; on the C++ backend the list the step
    of ``_biString`` would build, made natively in one call
    (``Node.create_string``).  The empty string is ``[]``.
    '''
    if not text:
      return self._mknode(self.prelude.Nil, target=target)
    if self.cxx:
      from ..backends.cxx import cyrtbindings
      target = getattr(target, 'target', target)
      return cyrtbindings.Node.create_string(text, target)
    from ..backends.py.currylib.prelude.string import codepoints
    return self._mknode(self.prelude._biString, codepoints(text), target=target)

  def _free_node(self, problem, spec):
    '''
    The shared node of a free marker: a call of ``Prelude.unknown`` applied
    to the ``Data`` dictionary of its type, made at the first occurrence of
    the marker under this interpreter and reused at every later one.  See
    :class:`curry.expressions.free`.
    '''
    marker = spec.payload
    node = None if marker is None else marker._shared(self.interp)
    if node is None:
      dictionary = self.dict_node(problem.free_dictionary(spec))
      node = self._mknode(self.prelude.unknown, dictionary)
      if marker is not None:
        marker._share(self.interp, node)
    self.count_freevar()
    return node

  def count_freevar(self):
    '''Counts a free variable made outside an evaluation; see ``RuntimeState.set_goal``.'''
    istate = self.interp.backend.get_interpreter_state(self.interp)
    istate.external_freevars += 1

  def _iterator_node(self, problem, spec, target):
    elemtype = problem.type_of(spec).args[0]
    items = iterate_typed(
        self.interp, spec.payload, elemtype, problem.location(spec)
      )
    return self._mknode(self.prelude._biGenerator, items, target=target)

  def _wrap_node(self, spec, child, target):
    make = self._mknode
    kind = spec.kind
    if kind == 'anchor':
      self.anchors[spec.extra] = child
      return self._forward(child, target)
    if kind == 'fwd':
      return make(self.fsyms.Fwd, child, target=target)
    if kind == 'setgrd':
      return make(self.fsyms.SetGuard, spec.extra, child, target=target)
    info = {
        'strict': self.fsyms.StrictConstraint
      , 'nonstrict': self.fsyms.NonStrictConstraint
      , 'binding': self.fsyms.ValueBinding
      }[kind]
    return make(info, child, self.raw_build(spec.extra), target=target)

# Iterators
# =========
def iterate_typed(interp, iterator, elemtype, where):
  '''
  Converts the items of ``iterator`` at ``elemtype`` as the list is
  demanded.  An item that does not convert ends the evaluation with an
  ``EvaluationError`` that names the item, the position and the type.
  '''
  convert = item_converter(interp, elemtype)
  for item in iterator:
    try:
      yield convert(item)
    except exceptions.CurryTypeError as err:
      raise exceptions.EvaluationError(
          'cannot convert item %r of the iterator at %s to %s'
              % (item, where, show_type(elemtype))
        ) from err

def item_converter(interp, elemtype):
  '''
  A function from a Python item to its node at ``elemtype``: a direct
  conversion for the ground types ``Int``, ``Float``, ``Char``, ``Bool`` and
  ``[Char]``, and the typed builder for everything else.
  '''
  make = interp.backend.make_node
  prelude = interp.prelude
  name = None
  if isinstance(elemtype, fc.TCons):
    if not elemtype.args:
      name = elemtype.name
    elif elemtype.name == LIST and elemtype.args == [fc.TCons(CHAR, [])]:
      name = LIST
  def general(item):
    return build(interp, (item,), {}, exprtype=elemtype)
  def reject(item, what):
    raise exceptions.CurryTypeError(
        'cannot convert %r to %s' % (item, what)
      )
  if name == INT:
    def convert(item):
      if isinstance(item, numbers.Integral) and not isinstance(item, bool):
        return make(prelude.Int, int(item))
      return general(item)
  elif name == FLOAT:
    def convert(item):
      if isinstance(item, numbers.Real) and not isinstance(item, bool):
        return make(prelude.Float, float(item))
      return general(item)
  elif name == CHAR:
    def convert(item):
      if isinstance(item, str) and len(item) == 1:
        return make(prelude.Char, item)
      return general(item)
  elif name == BOOL:
    def convert(item):
      if isinstance(item, bool):
        return make(prelude.True_ if item else prelude.False_)
      return general(item)
  elif name == LIST:
    strings_ = TypedBuilder(interp)
    def convert(item):
      if isinstance(item, (str, bytes)):
        return strings_.string_node(strings.ensure_str(item))
      return general(item)
  else:
    convert = general
  return convert

# The problem
# ===========
class TypedProblem(Problem):
  '''
  The engine's problem with the specs of the builder: a value typed by a
  walk of its content, the wrappers, the references and the groups.
  '''
  def __init__(self, builder, root, exprtype=None):
    self.builder = builder
    self._anchor_types = {}
    Problem.__init__(self, builder.interp, root, exprtype=exprtype)

  def anchor_type(self, key):
    '''The type variable of an anchor in this problem, shared with its references.'''
    var = self._anchor_types.get(key)
    if var is None:
      var = self._anchor_types[key] = Var()
    return var

  def _enter(self, spec, expected):
    if isinstance(spec, Raw):
      if spec.walk and not isinstance(spec.parent, Typed):
        spec.type = self._walk(spec, spec.payload)
      elif spec.typeexpr is not None:
        spec.type = spec.typeexpr
      else:
        spec.type = Var()
        self._env_vars.append(spec.type)
      self._expect(spec, expected)
      return ()
    if isinstance(spec, Wrap):
      spec.type = self.anchor_type(spec.extra) if spec.kind == 'anchor' else Var()
      self._expect(spec, expected)
      return [(spec.items[0], spec.type)]
    if isinstance(spec, Group):
      spec.type = Var()
      self._expect(spec, expected)
      children = [(item, None) for item in spec.items[:-1]]
      children.append((spec.items[-1], spec.type))
      return children
    if isinstance(spec, Ref):
      spec.type = self.anchor_type(spec.payload)
      self._expect(spec, expected)
      return ()
    if isinstance(spec, Unboxed):
      # The marker outside the payload of a primitive, or a payload that
      # does not fit its primitive (the class says where it stands).  A
      # node is expected at the position of the marker, and the raw value
      # in its place is an ill-formed node, which ended the process on the
      # C++ backend; a payload of the wrong Python type is a node whose
      # bits mean another value there (issue #107).
      where = self.location(spec)
      raise errors.ConversionError(
          self.builder.X.unboxed_message(spec.payload, where, spec.primitive)
        , where=where, value=spec.payload
        )
    return Problem._enter(self, spec, expected)

  def _resolve(self, pred):
    # A free variable under a rigid type variable of exprtype stays
    # polymorphic: it gets the placeholder dictionary, as a variable the
    # defaulting left polymorphic does.
    if pred.instance is None and pred.classname == DATA_CLASS \
        and isinstance(whnf(pred.term, self.arity), Rigid):
      return self.placeholder()
    return Problem._resolve(self, pred)

  def _walk(self, spec, root):
    '''
    The type of a Curry value: a walk of its content, to the leaves, with
    an explicit stack.  A constructor or function node is typed by the
    scheme of its symbol unified with the types of its arguments; a partial
    application by the scheme of its head unified with the arguments it
    holds, which leaves the function type of the missing ones; a node
    without a scheme, a free variable and a failure are opaque leaves.

    A memo per node serves the nodes with node successors, the primitives,
    the strings, the generators and the free variables, so a shared
    subgraph is visited once, a cycle ends, and a variable has one type.  A
    node without node successors, such as ``[]``, ``Nothing``, ``id`` or a
    failure, is not in the memo: it is typed at every position it holds,
    with a fresh instance of its scheme, because the runtime shares one
    such node between positions of different types (on the C++ backend one
    ``[]`` serves every empty list, and compiled code spells a constant
    once on either backend), so the sharing says nothing about the type
    (issue #108).  Every position of such a node counts towards the cap;
    a node of the memo counts once.

    The walk stops at :data:`VALUE_WALK_CAP` nodes, and a type that would
    print with more than that many nodes is refused as well: the type of a
    value that shares a node between the components of a pair at every
    level is exponential in its size.
    '''
    interp = self.interp
    # The record is the shortcut for a node curry.expr returned: its type
    # holds after an evaluation, which rewrites the node to its value.
    entry = record_of(interp).get(root)
    if entry is not None:
      mapping = {}
      t = terms.instantiate(entry[1], mapping)
      self._env_vars.extend(mapping.values())
      return t
    symbols = symbol_map(interp)
    table = interp.sigtable
    cap = VALUE_WALK_CAP
    memo = {}  # the id of a node -> its type variable, at its first visit
    count = 0
    rootvar = Var()
    # An entry of the stack is a node with its type variable, and None
    # before its children are typed, else the frame that types it: the
    # parameter types, the result type and the variables of the children.
    # A child is pushed with a fresh variable; the visit decides whether
    # the node enters the memo, from the successors it reads anyway.
    stack = [(_follow(root), rootvar, None)]
    while stack:
      node, var, frame = stack.pop()
      if frame is not None:
        params, restype, childvars = frame
        for childvar, param in zip(childvars, params):
          self._unify(childvar, param, spec)
        self._unify(var, restype, spec)
        continue
      known = memo.get(node.id())
      if known is not None:
        # A shared node pushed twice before its first visit: one type.
        self._unify(var, known, spec)
        continue
      count += 1
      if count > cap:
        raise errors.ValueTooLargeError(self.location(spec), cap)
      info = node.info
      children = ()
      params = ()
      restype = var
      shared = True  # whether the node enters the memo
      if info.is_primitive:
        if info.is_int:
          restype = tcons('Int')
        elif info.is_char:
          restype = tcons('Char')
        else:
          restype = tcons('Float')
      elif inspect.isa_freevar(node):
        memo[node.id()] = var
        self._env_vars.append(var)
        continue
      elif inspect.isa_failure(node):
        self._env_vars.append(var)
        continue
      elif inspect.isa_choice(node):
        children = [_follow(node.successor(1)), _follow(node.successor(2))]
        params = [var, var]
      elif inspect.isa_setguard(node):
        children = [_follow(node.successor(1))]
        params = [var]
      elif inspect.isa_constraint(node):
        children = [_follow(node.successor(0))]
        params = [var]
      elif info.is_io:
        inner = Var()
        children = [_follow(node.successor(0))]
        params = [inner]
        restype = tcons('IO', inner)
      elif info.name == STRING_NODE:
        restype = tcons('[]', tcons('Char'))
      elif info.name == GENERATOR_NODE:
        inner = Var()
        self._env_vars.append(inner)
        restype = tcons('[]', inner)
      else:
        head, stored = info, node.successors
        if info.is_partial:
          head, stored = _partial_parts(node)
        stored = [s for s in stored if isinstance(s, backends.Node)]
        shared = bool(stored)
        if shared:
          memo[node.id()] = var
        symbol = None if head is None else symbols.get(id(head))
        scheme = None if symbol is None else table.lookup(symbol)
        skip = scheme.ndicts if scheme is not None and head.tag == T_FUNC else 0
        if scheme is None or (info.is_partial and len(stored) < skip):
          # No scheme, or a partial application of a method without its
          # dictionaries: an opaque leaf.
          self._env_vars.append(var)
          continue
        mapping = {}
        kinds = dict(scheme.typevars)
        t = terms.instantiate(scheme.typeexpr, mapping, kinds)
        values = stored[skip:]
        params = []
        for _ in values:
          t = whnf(t, self.arity)
          if isinstance(t, fc.FuncType):
            params.append(t.domain)
            t = t.range
          elif isinstance(t, Var):
            domain, range_ = Var(), Var()
            self._unify(t, fc.FuncType(domain, range_), spec)
            params.append(domain)
            t = range_
          else:
            break
        children = [_follow(child) for child in values[:len(params)]]
        restype = t
      if shared:
        memo[node.id()] = var
      # A child in the memo has its variable already and is not visited
      # again; any other child gets a fresh variable at this position.
      childvars = []
      pending = []
      for child in children:
        childvar = memo.get(child.id())
        if childvar is None:
          childvar = Var()
          pending.append((child, childvar, None))
        childvars.append(childvar)
      stack.append((node, var, (params, restype, childvars)))
      stack.extend(reversed(pending))
    t = rootvar
    if terms.tree_size(t, cap) > cap:
      raise errors.ValueTooLargeError(
          self.location(spec), cap, what='type of the value'
        )
    return t

# The entry points
# ================
def build(interp, args, anchors, exprtype=None, target=None):
  '''
  ``curry.expr`` on the typed path.  A bare node alone passes through
  untouched when no type is asked of it.
  '''
  if len(args) == 1 and not anchors and exprtype is None:
    arg = args[0]
    arg = getattr(arg, 'rvalue', arg)
    if isinstance(arg, backends.Node):
      if target is not None:
        return interp.backend.make_node(
            interp.backend.fundamental_symbols.Fwd, arg, target=target
          )
      return arg
  builder = TypedBuilder(interp, target=target)
  root = builder.specs(args, anchors)
  return builder.run(root, exprtype)

class Description:
  '''
  The description of an expression: the spec tree of the arguments of
  ``curry.expr``, with the anchors of its keyword arguments and its
  ``exprtype``.  It is typed when a consumer asks: ``curry.expr(description)``
  or ``curry.eval(description)`` build its node, :meth:`typeof` gives its
  type, and each typing starts afresh.  A description may be an argument of
  a larger one; its anchors travel with it, and a reference outside the
  description cannot name them.  ``str`` prints it in Curry syntax.
  '''
  def __init__(self, interp, args, anchors=None, exprtype=None):
    self.interp = interp
    self.exprtype = exprtype
    self.builder = TypedBuilder(interp)
    self.root = self.builder.specs(args, anchors or {})

  def __str__(self):
    return describe(self.root)

  def __repr__(self):
    return '<curry description %s>' % self

  def typeof(self, defaulted=False):
    '''The type of the expression in Curry syntax; see :func:`typeof`.'''
    return typeof(self.interp, self, defaulted)

  def build(self, exprtype=None, target=None):
    '''The node of the expression; ``exprtype`` overrides the description's.'''
    return build_description(self, exprtype, target)

def build_description(description, exprtype=None, target=None):
  if exprtype is None:
    exprtype = description.exprtype
  builder = TypedBuilder(description.interp, target=target)
  builder.anchor_vars = description.builder.anchor_vars
  builder.anchors = dict.fromkeys(description.builder.anchors)
  return builder.run(description.root, exprtype)

def typeof(interp, e, defaulted=False):
  '''
  The type of an expression in Curry syntax: the undefaulted scheme, what
  ``:type`` prints, or the defaulted type.  ``e`` is a node ``curry.expr``
  returned (its recorded type) or any other Curry node (typed by its
  content), a symbol, a :class:`Description`, or any argument of
  ``curry.expr``.
  '''
  e = getattr(e, 'rvalue', e)
  if isinstance(e, backends.Node):
    entry = record_of(interp).get(e)
    if entry is not None:
      scheme, typeexpr = entry
      return show_type(typeexpr) if defaulted else str(scheme)
    problem = TypedProblem(TypedBuilder(interp), Raw(e, walk=True))
  elif isinstance(e, Description):
    problem = TypedProblem(e.builder, e.root, e.exprtype)
  elif isinstance(e, CurryNodeInfo) and e.scheme is None:
    # curry.expr builds a lone symbol without a scheme untyped; its type is
    # unknown, not a variable.
    interp.sigtable.lookup(e, required=True)
    raise exceptions.CurryTypeError('no type for %s' % _symbol_name(e))
  else:
    builder = TypedBuilder(interp)
    problem = TypedProblem(builder, builder.specs((e,)))
  if defaulted:
    problem.solve()
    return problem.defaulted_signature
  return problem.signature
