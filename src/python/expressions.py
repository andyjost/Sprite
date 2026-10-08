'''
Building Curry expressions from Python.

``expr`` is the typed builder: it types the expression over the schemes of
the front end, converts Python values by the expected type, and supplies
the class dictionaries (see :mod:`curry.typecheck.builder`).  ``raw_expr``
is the untyped builder, which converts by the Python type alone and checks
only the arity; it serves the runtime and the tests of the runtime.  The
markers of this module (:class:`anchor`, :class:`choice`, :class:`cons`,
:data:`fail`, :class:`free`, :data:`nil`, :class:`ref`, :class:`typed`,
:class:`unboxed`) describe the parts of an expression that are no Python
value.
'''

from . import backends, config, icurry, objects, utility
from .common import T_FUNC
from .exceptions import CurryTypeError
from .utility import strings, visitation
import collections.abc, itertools, numbers, weakref

__all__ = [
    'anchor', 'choice', 'cons', 'describe', 'expr', 'fail', 'fwd', 'free'
  , 'nil', 'raw_expr', 'ref', 'result_type', 'typed', 'typeof', 'unboxed'
  , 'untyped_expr'
  ]

class anchor(object):
  '''
  Used with :func:`expr` to create an anchor in an expression.  This can be
  used to construct nonlinear expressions.

  When no argument is supplied, the anchor name is automatically generated from
  the sequence _1, _2, ..., according to its position in a left-to-right,
  depth-first traversal.
  '''
  def __init__(self, value, name=None):
    self.value = value
    self.name = name

class ref(object):
  '''
  Used with :func:`expr` to create a reference to a named subexpression.
  This can be used to construct nonlinear expressions.

  The argument is optional when the expression contains exactly one anchor at
  the point where the reference appears.
  '''
  def __init__(self, name=None):
    self.name = name

class cons(object):
  '''
  Used with :func:`expr` to place one or more list constructors into a Curry
  expression.
  '''
  def __init__(self, head, tail0, *tail):
    self.head = head
    if tail:
      self.tail = cons(tail0, *tail)
    else:
      self.tail = tail0

class _nilcls(object): pass
nil = _nilcls()
'''
Used with :func:`expr` to place a list terminator into a Curry expression.
'''
del _nilcls

class unboxed(object):
  '''
  Used with :func:`expr` to place the unboxed payload of a primitive into a
  Curry expression: ``[Prelude.Int, curry.unboxed(3)]`` is the node ``<Int
  3>``, and ``Prelude.Char`` and ``Prelude.Float`` take the marker the same
  way.  A plain Python value builds the same node, so the marker is seldom
  needed.  The payload must fit the primitive: a Python ``int`` under
  ``Int``, a ``str`` of length one under ``Char``, a ``float`` under
  ``Float``; another value is a ``CurryTypeError`` from both builders
  (:func:`unboxed_payload`).  Anywhere else the marker is a
  ``CurryTypeError`` at construction, from both builders: alone, in a list
  or a tuple, or as the argument of another symbol, a node is expected, and
  an unboxed value in its place is an ill-formed node, which ended the
  process on the C++ backend (issue #107).  An item of an iterator is
  converted when the list is demanded, so the marker there is an
  ``EvaluationError`` at that time.
  '''
  def __init__(self, value):
    if not isinstance(value, icurry.IUnboxedLiteral):
      raise CurryTypeError('expected an unboxed literal, got %r' % value)
    self.value = value

  def __repr__(self):
    return 'curry.unboxed(%r)' % (self.value,)

# The primitive of a payload: its name, the Python type the payload must
# have, and the example of the messages.
_PRIMITIVES = {
    'Int': (int, 'a Python int', 3)
  , 'Char': (str, 'a str of length one', 'a')
  , 'Float': (float, 'a Python float', 2.5)
  }

def primitive_name(info):
  '''The type name of a primitive info table: Int, Char or Float.'''
  return 'Int' if info.is_int else 'Char' if info.is_char else 'Float'

def unboxed_fits(primitive, value):
  '''
  Whether ``value`` is the payload of the primitive named ``primitive``: a
  Python ``int`` under ``Int`` (a ``bool`` is not one), a ``str`` of length
  one under ``Char``, a ``float`` under ``Float``.  Another value makes a
  node whose bits mean another value on the C++ backend, and a node the
  Python backend cannot evaluate.
  '''
  pytype = _PRIMITIVES[primitive][0]
  if not isinstance(value, pytype) or isinstance(value, bool):
    return False
  return primitive != 'Char' or len(value) == 1

def unboxed_payload(info, value, where=None):
  '''
  The payload of ``curry.unboxed`` under the primitive ``info``, checked:
  the value itself, or a ``CurryTypeError`` when it does not fit
  (:func:`unboxed_fits`).  ``where`` is the text of the position in the
  typed builder, or None in the untyped builder.
  '''
  primitive = primitive_name(info)
  if not unboxed_fits(primitive, value):
    raise CurryTypeError(unboxed_message(value, where, primitive))
  return value

def unboxed_message(value, where=None, primitive=None):
  '''
  The message of an :class:`unboxed` marker outside the payload of a
  primitive, or, with ``primitive`` given, of a payload that does not fit
  that primitive.  ``where`` is the text of the position in the typed
  builder (``'the expression'`` for the marker alone), or None in the
  untyped builder, which does not know the position.
  '''
  if primitive is not None:
    _, pytype, example = _PRIMITIVES[primitive]
    place = '' if where is None else ' at ' + where
    return (
        'curry.unboxed(%r) is not the payload of %s %s%s; the payload of '
        '%s %s is %s, as in [Prelude.%s, curry.unboxed(%r)]'
            % ( value, _article(primitive), primitive, place
              , _article(primitive), primitive, pytype, primitive, example
              )
      )
  if isinstance(value, str):
    primitive = 'Char'
  elif isinstance(value, float):
    primitive = 'Float'
  else:
    primitive = 'Int'
  if where is None:
    place = 'outside a primitive'
  elif where == 'the expression':
    place = 'alone'
  else:
    place = 'at ' + where
  return (
      'curry.unboxed(%r) stands %s; the marker is the payload of an Int, '
      'Char or Float, as in [Prelude.%s, curry.unboxed(%r)]'
          % (value, place, primitive, value)
    )

def _article(primitive):
  return 'an' if primitive == 'Int' else 'a'

class _setgrd(object):
  '''Used with :func:`expr` to place a set guard into a Curry expression.'''
  def __init__(self, sid, value=None):
    if value is None:
      sid, value = 0, sid # shift right
    self.sid = int(sid)
    self.value = value

class _failcls(object): pass
fail = _failcls()
'''Used with :func:`expr` to place a failure into a Curry expression.'''
del _failcls

class _strictconstr(object):
  '''Used with :func:`expr` to place a strict constraint into a Curry expression.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class _nonstrictconstr(object):
  '''Used with :func:`expr` to place a nonstrict constraint into a Curry expression.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class _valuebinding(object):
  '''Used with :func:`expr` to place a value binding into a Curry expression.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class free(object):
  '''
  Used with :func:`expr` to place a free variable into a Curry expression.

  Through ``expr``, one marker is one variable.  The builder makes one node
  for the marker, a call of ``Prelude.unknown`` applied to the ``Data``
  dictionary of its type, and reuses it for every occurrence of the marker,
  in that expression and in later ones.  The first rewrite step on the node
  creates the variable with a fresh id and forwards the node to it.  The
  node belongs to one interpreter state: ``curry.reset`` installs a new
  state, and the marker becomes a new variable there.  ``exprtype`` fixes
  the type of the variable, in Curry syntax; without it the type comes from
  the context, and a variable whose type stays polymorphic gets the
  dictionary of ``Bool``, which ``unknown`` never reads.  Through
  ``raw_expr``, every occurrence is a separate ``Free`` node with the id
  ``vid``, 0 by default; that form serves the tests of the runtime.
  '''
  def __init__(self, vid=0, exprtype=None):
    self.vid = int(vid)
    self.exprtype = exprtype
    # The shared node and a weak reference to the interpreter state it was
    # built under.  See ExpressionBuilder.unknown.
    self._node = None
    self._istate = None

  def _shared(self, interp):
    '''
    The shared node of this marker under the current state of ``interp``, or
    None.  The key is the state, not the interpreter: ``Interpreter.reset``
    installs a new state with a new id factory, so a node built under the old
    state would share an id with the variables of the new one.
    '''
    istate = interp.backend.get_interpreter_state(interp)
    if self._istate is not None and self._istate() is istate:
      return self._node

  def _share(self, interp, node):
    istate = interp.backend.get_interpreter_state(interp)
    self._istate = weakref.ref(istate)
    self._node = node

class fwd(object):
  '''Used with :func:`expr` to place a forward node into a Curry expression.'''
  def __init__(self, value):
    self.value = value

class choice(object):
  '''
  Used with :func:`expr` to place a choice into a Curry expression.

  Through ``expr``, the choice is a call of ``Prelude.?``, whose rewrite step
  draws a fresh id from the interpreter; ``cid`` is not used.  Through
  ``raw_expr``, it is a ``Choice`` node with the id ``cid``, 0 by default.
  '''
  def __init__(self, cid, lhs, rhs=None):
    if rhs is None:
      cid, lhs, rhs = 0, cid, lhs # shift right
    self.cid = int(cid)
    self.lhs = lhs
    self.rhs = rhs

class typed(object):
  '''
  Used with :func:`expr` to annotate a part of an expression with its type:
  ``curry.typed(value, 'T')`` converts ``value`` at the type ``T``, in Curry
  syntax, and unifies ``T`` with the type the context expects.  So
  ``curry.typed('a', 'String')`` is the string ``"a"``, and
  ``curry.typed(node, '[Int]')`` states the type of a large value instead of
  a walk of its content.  ``raw_expr`` builds the value and ignores the
  annotation.
  '''
  def __init__(self, value, exprtype):
    self.value = value
    self.exprtype = exprtype

@utility.formatDocstring(config.python_package_name())
def expr(interp, *args, **kwds):
  '''
  Builds a Curry expression.

  The expression is typed before it is built (see
  :mod:`{0}.typecheck.builder`): the type schemes of the symbols are read
  from the FlatCurry interfaces of their modules, the arguments are unified
  with the parameter types, the class constraints are defaulted with the
  table of the PAKCS REPL, and the class dictionaries are supplied.  So
  ``expr(curry.symbol('Prelude.+'), 1, 2)`` builds the call of the method
  at ``Int``, and ``expr(P.show, [P.Just, 1])`` finds the ``Show`` instance
  of ``Maybe Int``.  A typing failure raises :class:`CurryTypeError
  <{0}.exceptions.CurryTypeError>` at construction; nothing is evaluated.
  The flag ``typed_expr`` turns the typing off.

  The arguments specify the expression to build.  Each positional argument
  must be directly convertible to Curry or describe a node.  A Python value
  converts by the type its position expects:

    * ``bool``:
      Converted to ``Prelude.Bool``.
    * ``int``
      ``Prelude.Int``; ``Prelude.Float`` under ``Float``; the ``fromInt``
      conversion under another ``Num`` instance.
    * ``float``
      Converted to ``Prelude.Float``.
    * ``str``
      Under ``[Char]`` one string of any length.  Elsewhere a string of
      length one is a ``Prelude.Char``, and another string is ``[Char]``.
    * ``list``
      Converted to a Curry list, in a loop.  Every element takes the element
      type, so ``[1, 2.5]`` is ``[Float]``.
    * ``tuple``
      Converted to a Curry tuple.
    * ``iterator``
      Lazily converted to a Curry list.  The element type is fixed when the
      expression is built; an item that does not convert ends the
      evaluation with an ``EvaluationError``.
    * ``None``
      An error that names the expected type.
    * a Curry node
      Typed by a walk of its content, up to 100000 nodes;
      ``curry.typed(node, 'T')`` states the type instead.  A node alone
      passes through untouched.

  Any (possibly nested) sequence whose first element is an instance of
  :class:`NodeInfo <{0}.objects.CurryNodeInfo>` specifies a node.  The remaining
  arguments are recursively converted to Curry expressions to form the
  successors list.  Thus, given suitable definitions, it is possible to build
  the Curry list ``[0,1,2]`` with the following code:

      expr([Cons, 0, [Cons, 1, [Cons, 2, Nil]]])

  Fewer arguments than the symbol takes give a partial application; more
  arguments go through ``Prelude.apply`` when the result is a function.  A
  symbol without a type scheme (a module without a FlatCurry interface, or
  a built-in of Sprite's own Prelude) is built untyped when it stands
  alone, as the goal of a saved module does, and is an error when it is
  applied to arguments; :func:`typeof` refuses it either way.

  Several special symbols are provided.  See :class:`anchor`, :class:`choice`,
  :class:`cons`, :data:`fail`, :class:`free`, :data:`nil`, :class:`ref`,
  :class:`typed`, and :class:`unboxed`.  A :class:`free` marker becomes a
  call of ``Prelude.unknown``, one node per marker, and a :class:`choice`
  marker a call of ``Prelude.?``, so the runtime assigns the ids.
  ``raw_expr`` builds the raw ``Free`` and ``Choice`` nodes instead.  An
  :class:`unboxed` marker stands only as the payload of a primitive,
  ``[Prelude.Int, curry.unboxed(3)]``; anywhere else it is a
  ``CurryTypeError``.

  Args:
    interp:
        An interpreter object.
    *args:
        Positional arguments used to construct expressions.
    **kwds:
        Keyword arguments specifying subexpressions that may be referenced via
        ``ref``.  Each keyword specifies the name of an anchor.  See the
        examples below.
    exprtype:
        Keyword-only argument.  The type of the expression in Curry syntax,
        for example ``'Maybe Float'``.  Its type variables are rigid.
    target:
        Reserved keyword-only argument.  If a target is supplied, then it will
        be rewritten with the specified expression.  Otherwise a new node is
        created.

  Returns:
    A Curry expression.  Its type is recorded, so :func:`typeof` answers for
    it, and ``eval`` converts its values by it.
  '''
  exprtype = kwds.pop('exprtype', None)
  if interp.flags.get('typed_expr', True):
    from .typecheck import builder
    target = kwds.pop('target', None)
    return builder.build(interp, args, kwds, exprtype=exprtype, target=target)
  return _build(interp, args, kwds, raw=False)

def raw_expr(interp, *args, **kwds):
  '''
  The untyped builder.  Equivalent to :func:`expr` without the types: every
  Python value converts by its Python type, only the arity of a symbol is
  checked, no dictionary is supplied, a :class:`free` marker becomes a raw
  ``Free`` node with the id of the marker, a new node per occurrence, and a
  :class:`choice` marker a raw ``Choice`` node with the id of the marker.
  Fewer arguments than the arity of a symbol give a partial application; a
  function applied to more goes through ``Prelude.apply``, one node per
  surplus argument, as a point-free definition needs; a constructor applied
  to more is an error.  An expression that is not well typed evaluates with
  undefined behaviour.
  '''
  return _build(interp, args, kwds, raw=True)

def untyped_expr(interp, *args, **kwds):
  '''
  The untyped builder with the markers of :func:`expr`: a :class:`free`
  marker is its shared ``unknown`` node and a :class:`choice` marker a call
  of ``Prelude.?``.  This is :func:`expr` with the flag ``typed_expr`` off.
  The interpreter uses it for the expressions it builds around compiled
  code, whose types the front end checked.
  '''
  kwds.pop('exprtype', None)
  return _build(interp, args, kwds, raw=False)

def typeof(interp, e, defaulted=False):
  '''
  The type of an expression in Curry syntax.  Without ``defaulted`` the
  undefaulted scheme, what ``:type`` prints: ``typeof(expr(plus, 1, 2))``
  is ``Num a => a``.  With ``defaulted`` the type after the table of the
  PAKCS REPL: ``Int``.  ``e`` is a node :func:`expr` returned, any other
  Curry node (typed by its content), a symbol, a description of
  :func:`describe`, or any argument :func:`expr` accepts.
  '''
  from .typecheck import builder
  return builder.typeof(interp, e, defaulted)

def describe(interp, *args, **kwds):
  '''
  The description of an expression: the arguments of :func:`expr` as a
  tree, typed only when a consumer asks for its node.  The DSL builds
  descriptions at every operator and types them once at the boundary, so
  that an outer context fixes the types of the inner parts.  A description
  is an argument of :func:`expr` and of ``eval``; ``str`` prints it in
  Curry syntax; its method ``typeof`` gives its type.  The keyword
  ``exprtype`` states the type of the description; the other keywords are
  its anchors.  See :class:`Description <curry.typecheck.builder.Description>`.
  '''
  from .typecheck import builder
  exprtype = kwds.pop('exprtype', None)
  if 'target' in kwds:
    raise TypeError('describe() takes no target; pass it to expr or to build')
  return builder.Description(interp, args, kwds, exprtype=exprtype)

def result_type(interp, node):
  '''The defaulted type :func:`expr` recorded for a node, or None.'''
  from .typecheck import builder
  return builder.result_type(interp, node)

def _build(interp, args, kwds, raw):
  builder = ExpressionBuilder(interp, raw=raw)
  target = kwds.pop('target', None)
  for anchorname, subexpr in kwds.items():
    subexpr = anchor(subexpr, name=anchorname)
    builder(subexpr)
    assert anchorname in builder.anchors
  builder.target = target
  expr = builder(*args)
  return builder.fixrefs(expr)

def fix_references(expr, brokenrefs, anchors):
  '''
  Replaces the placeholders of the references that were built before their
  anchors.  ``brokenrefs`` maps the id of a placeholder to the key of its
  anchor in ``anchors``.
  '''
  if brokenrefs:
    from .backends.py.graph.walkexpr import walk
    for state in walk(expr):
      if isinstance(state.cursor, backends.Node):
        key = brokenrefs.get(state.cursor.id())
        if key is not None:
          parent = state.parent
          if parent is None:
            # This is the trivial cycle a=a.
            state.cursor.forward_to(state.cursor)
          else:
            parent.set_successor(state.realpath[-1], anchors[key])
        else:
          state.push()
  return expr

# The dictionary argument of Prelude.unknown.  The body of unknown declares a
# free variable and returns it; it never reads the dictionary.  The untyped
# builder does not know the type of a marker, so the dictionary of Bool
# stands in.
UNKNOWN_DICTIONARY = 'Prelude._inst#Prelude.Data#Prelude.Bool'

class ExpressionBuilder(object):
  '''
  Implementation of ``raw_expr``, and of ``expr`` with the flag
  ``typed_expr`` off.  With ``raw`` set, a free marker becomes a raw
  ``Free`` node and a choice marker a raw ``Choice`` node, as the tests of
  the runtime expect.  Otherwise the markers become calls of
  ``Prelude.unknown`` and ``Prelude.?``, so that the runtime assigns the
  ids (see :class:`free` and :class:`choice`).  A :class:`typed` marker
  builds its value; the annotation is ignored.
  '''
  def __init__(self, interp, raw=False):
    self.interp = interp
    self.raw = raw
    self.counter = itertools.count(1)
    self.anchors = {}
    self.brokenrefs = {}
    self.target = None
    self._mknode = interp.backend.make_node
    self.prelude = self.interp.prelude
    self.fsyms = self.interp.backend.fundamental_symbols

  def fixrefs(self, expr):
    return fix_references(expr, self.brokenrefs, self.anchors)

  @visitation.dispatch.on('arg')
  def __call__(self, arg, *args, **kwds):
    if hasattr(arg, 'rvalue'): # handle Variable
      return self(arg.rvalue, *args, **kwds)
    raise TypeError(
        'cannot build a Curry expression from type %r' % type(arg).__name__
      )

  @__call__.when((str, bytes)) # Char or [Char].
  def __call__(self, arg, *trailing):
    arg = strings.ensure_str(arg)
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    if len(arg) == 1:
      return self._mknode(self.prelude.Char, str(arg), target=self.target)
    else:
      return self(list(arg))

  @__call__.when(list)
  def __call__(self, lst, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % lst)
    if len(lst) and isinstance(lst[0], (objects.CurryNodeInfo, backends.InfoTable)):
      return self(*lst)
    else:
      Cons = self.prelude.Cons
      Nil = self.prelude.Nil
      sentinel = object()
      seq = iter(lst)
      f = lambda x,g: [Cons, self(x), g()] if x is not sentinel else Nil
      g = lambda: f(next(seq, sentinel), g)
      return self(g())

  @__call__.when(tuple)
  def __call__(self, tup, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %s' % repr(tup))
    n = len(tup)
    if n == 0:
      typename = 'Prelude.()'
    elif n == 1:
      raise CurryTypeError("Curry has no 1-tuple.")
    else:
      typename = 'Prelude.(%s)' % (','*(n-1))
    return self._mknode(
        self.interp.symbol(typename), *map(self, tup), target=self.target
      )

  @__call__.when(bool)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    if arg:
      return self._mknode(self.prelude.True_, target=self.target)
    else:
      return self._mknode(self.prelude.False_, target=self.target)

  @__call__.when(numbers.Integral)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    return self._mknode(self.prelude.Int, int(arg), target=self.target)

  @__call__.when(numbers.Real)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    return self._mknode(
        self.prelude.Float, float(arg), target=self.target
      )

  @__call__.when(anchor)
  def __call__(self, arg, *trailing):
    if arg.name is None:
      while True:
        anchorname = '_%s' % next(self.counter)
        if anchorname not in self.anchors:
          break
    else:
      anchorname = arg.name
    if trailing:
      raise CurryTypeError('invalid arguments after anchor %r' % anchorname)
    if anchorname in self.anchors:
      raise ValueError('multiple definitions of anchor %r' % anchorname)
    self.anchors[anchorname] = None
    subexpr = self(arg.value)
    self.anchors[anchorname] = subexpr
    return subexpr

  @__call__.when(ref)
  def __call__(self, arg, *trailing):
    if arg.name is None:
      if len(self.anchors) != 1:
        raise ValueError(
            "invalid use of unqualified 'ref' with %s anchors defined"
                % len(self.anchors)
          )
      anchorname = next(iter(self.anchors))
    else:
      anchorname = arg.name
    if trailing:
      raise CurryTypeError('invalid arguments after ref %r' % anchorname)
    target = self.anchors.get(anchorname)
    if target is None:
      # The placeholder must be a fresh node that can be forwarded: fixrefs
      # forwards it to itself for the trivial cycle a=a.  A failure will not
      # do, because on the C++ backend failures are one shared node that is
      # too small to forward.
      placeholder = self(fwd(fail))
      self.brokenrefs[placeholder.id()] = anchorname
      return placeholder
    else:
      return target

  @__call__.when(collections.abc.Iterator)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % arg)
    pygen = self.prelude._biGenerator
    arg = (self(x) for x in arg)
    return self._mknode(pygen, arg, target=self.target)

  @__call__.when((objects.CurryNodeInfo, backends.InfoTable))
  def __call__(self, ti, *args):
    info = getattr(ti, 'info', ti)
    arity = info.arity
    if info.is_primitive and len(args) == 1 and isinstance(args[0], unboxed):
      # A boxed literal over its unboxed payload, [Int, unboxed(3)]: the one
      # place of the marker.  The payload must fit the primitive.  See the
      # handler of unboxed below.
      payload = unboxed_payload(info, args[0].value)
      return self._mknode(ti, payload, target=self.target)
    if len(args) <= arity:
      partial_info = self.fsyms.PartApplic if len(args) < arity else None
      return self._mknode(
          ti, *map(lambda s: self(s), args), target=self.target
        , partial_info=partial_info
        )
    # More arguments than the arity.  A function may return a function, as a
    # point-free definition does, so the surplus goes through Prelude.apply,
    # one node per argument, as the typed builder does.  A constructor
    # returns data: the application is an error here, not at the node.
    if info.tag != T_FUNC:
      # The sentence of the typed builder (typecheck.errors.ArityError)
      # without the scheme: this builder knows the arity alone.
      raise CurryTypeError(
          '%s takes %d argument%s, %d given'
              % (info.name, arity, '' if arity == 1 else 's', len(args))
        )
    head, rest = args[:arity], args[arity:]
    apply_ = self.prelude.apply
    node = self._mknode(ti, *map(lambda s: self(s), head))
    for i, extra in enumerate(rest):
      node = self._mknode(
          apply_, node, self(extra)
        , target=self.target if i == len(rest) - 1 else None
        )
    return node

  @__call__.when(backends.Node)
  def __call__(self, node, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r node' % node.info.name)
    if self.target is not None:
      return self._mknode(self.fsyms.Fwd, node, target=self.target)
    return node

  @__call__.when(unboxed)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after unboxed %r' % arg.value)
    # The symbol handler takes the marker under a primitive before it gets
    # here, so this marker stands alone, in a list or a tuple, or as the
    # argument of another symbol: a node is expected there, and the raw
    # value in its place is an ill-formed node, which the C++ backend
    # dereferenced at construction (issue #107).
    raise CurryTypeError(unboxed_message(arg.value))

  @__call__.when(typed)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'typed')
    return self(arg.value)

  @__call__.when(cons)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'cons')
    return self._mknode(
        self.prelude.Cons, self(arg.head), self(arg.tail)
      , target=self.target
      )

  @__call__.when(type(nil))
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'nil')
    return self._mknode(self.prelude.Nil, target=self.target)

  @__call__.when(_setgrd)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_setgrd')
    return self._mknode(
        self.fsyms.SetGuard
      , arg.sid, self(arg.value), target=self.target
      )

  @__call__.when(type(fail))
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'fail')
    return self._mknode(self.fsyms.Failure, target=self.target)

  @__call__.when(_strictconstr)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_strictconstr')
    return self._mknode(
        self.fsyms.StrictConstraint
      , self(arg.value), self(arg.pair), target=self.target
      )

  @__call__.when(_nonstrictconstr)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_nonstrictconstr')
    return self._mknode(
        self.fsyms.NonStrictConstraint
      , self(arg.value), self(arg.pair), target=self.target
      )

  @__call__.when(_valuebinding)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % '_valuebinding')
    return self._mknode(
        self.fsyms.ValueBinding
      , self(arg.value), self(arg.pair), target=self.target
      )

  @__call__.when(free)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'free')
    self.count_freevar()
    if self.raw:
      return self._mknode(
          self.fsyms.Free
        , arg.vid
        , self._mknode(self.prelude.Unit)
        , target=self.target
        )
    node = self.unknown(arg)
    if self.target is not None:
      return self._mknode(self.fsyms.Fwd, node, target=self.target)
    return node

  def unknown(self, marker):
    '''
    The shared node of a free marker: a call of ``Prelude.unknown`` applied
    to a ``Data`` dictionary, made at the first occurrence of the marker
    under this interpreter and reused at every later one.  The rewrite step
    of ``unknown`` creates the variable with a fresh id, registers it with
    the evaluation, and forwards this node to it.  So one marker is one
    variable, on both backends, and a later goal that holds the marker
    holds the variable (see RuntimeState.set_goal).
    '''
    node = marker._shared(self.interp)
    if node is None:
      dictionary = self.interp.symbol(UNKNOWN_DICTIONARY)
      partial_info = self.fsyms.PartApplic if dictionary.info.arity else None
      node = self._mknode(
          self.prelude.unknown
        , self._mknode(dictionary, partial_info=partial_info)
        )
      marker._share(self.interp, node)
    return node

  def count_freevar(self):
    '''
    Counts a free variable made outside an evaluation, so that
    ``RuntimeState.set_goal`` registers the variables a goal already holds.
    See ``InterpreterState.external_freevars`` of either backend.
    '''
    istate = self.interp.backend.get_interpreter_state(self.interp)
    istate.external_freevars += 1

  @__call__.when(fwd)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'fwd')
    return self._mknode(
        self.fsyms.Fwd, self(arg.value), target=self.target
      )

  @__call__.when(choice)
  def __call__(self, arg, *trailing):
    if trailing:
      raise CurryTypeError('invalid arguments after %r' % 'choice')
    if self.raw:
      return self._mknode(
          self.fsyms.Choice, arg.cid, self(arg.lhs), self(arg.rhs)
        , target=self.target
        )
    return self._mknode(
        getattr(self.prelude, '?'), self(arg.lhs), self(arg.rhs)
      , target=self.target
      )
