from . import backends, config, icurry, objects, utility
from .exceptions import CurryTypeError
from .utility import strings, visitation
import collections.abc, itertools, numbers, weakref

__all__ = [
    'anchor', 'choice', 'cons', 'expr', 'fail', 'fwd', 'free', 'nil'
  , 'raw_expr', 'ref', 'unboxed'
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
  Used with :func:`expr` to place an unboxed argument into a Curry expression.
  '''
  def __init__(self, value):
    if not isinstance(value, icurry.IUnboxedLiteral):
      raise CurryTypeError('expected an unboxed literal, got %r' % value)
    self.value = value

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
  for the marker, a call of ``Prelude.unknown``, and reuses it for every
  occurrence of the marker, in that expression and in later ones.  The first
  rewrite step on the node creates the variable with a fresh id and forwards
  the node to it.  The node belongs to one interpreter state: ``curry.reset``
  installs a new state, and the marker becomes a new variable there.
  Through ``raw_expr``, every occurrence is a separate
  ``Free`` node with the id ``vid``, 0 by default; that form serves the tests
  of the runtime.
  '''
  def __init__(self, vid=0):
    self.vid = int(vid)
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

@utility.formatDocstring(config.python_package_name())
def expr(interp, *args, **kwds):
  '''
  Builds a Curry expression.

  The arguments specify the expression to build.  Each positional argument must
  be directly convertible to Curry or describe a node.  The following direct
  conversions are recognized:

    * ``bool``:
      Converted to ``Prelude.Bool``.
    * ``float``
      Converted to ``Prelude.Float``.
    * ``int``
      Converted to ``Prelude.Int``.
    * ``iterator``
      Lazily Converted to a Curry list.
    * ``list``
      Eagerly Converted to a Curry list.
    * ``str``
      For strings of length one, ``Prelude.Char``.  Otherwise, ``[Prelude.Char]``.
    * ``tuple``
      Converted to a Curry tuple.

  Any (possibly nested) sequence whose first element is an instance of
  :class:`NodeInfo <{0}.objects.CurryNodeInfo>` specifies a node.  The remaining
  arguments are recursively converted to Curry expressions to form the
  successors list.  Thus, given suitable definitions, it is possible to build
  the Curry list ``[0,1,2]`` with the following code:

      expr([Cons, 0, [Cons, 1, [Cons, 2, Nil]]])

  Several special symbols are provided.  See :class:`anchor`, :class:`choice`,
  :class:`cons`, :data:`fail`, :class:`free`, :data:`nil`, :class:`ref`, and
  :class:`unboxed`.  A :class:`free` marker becomes a call of
  ``Prelude.unknown``, one node per marker, and a :class:`choice` marker a
  call of ``Prelude.?``, so the runtime assigns the ids.  ``raw_expr`` builds
  the raw ``Free`` and ``Choice`` nodes instead.

  Args:
    interp:
        An interpreter object.
    *args:
        Positional arguments used to construct expressions.
    **kwds:
        Keyword arguments specifying subexpressions that may be referenced via
        ``ref``.  Each keyword specifies the name of an anchor.  See the
        examples below.
    target:
        Reserved keyword-only argument.  If a target is supplied, then it will
        be rewritten with the specified expression.  Otherwise a new node is
        created.

  Returns:
    A Curry expression.
  '''
  return _build(interp, args, kwds, raw=False)

def raw_expr(interp, *args, **kwds):
  '''
  Equivalent to expr, except that a :class:`free` marker becomes a raw
  ``Free`` node with the id of the marker, a new node per occurrence, and a
  :class:`choice` marker a raw ``Choice`` node with the id of the marker.
  '''
  return _build(interp, args, kwds, raw=True)

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

# The dictionary argument of Prelude.unknown.  The body of unknown declares a
# free variable and returns it; it never reads the dictionary.  The builder
# does not know the type of a marker, so the dictionary of Bool stands in.
UNKNOWN_DICTIONARY = 'Prelude._inst#Prelude.Data#Prelude.Bool'

class ExpressionBuilder(object):
  '''
  Implementation of ``expr`` and ``raw_expr``.  With ``raw`` set, a free
  marker becomes a raw ``Free`` node and a choice marker a raw ``Choice``
  node, as the tests of the runtime expect.  Otherwise the markers become
  calls of ``Prelude.unknown`` and ``Prelude.?``, so that the runtime assigns
  the ids (see :class:`free` and :class:`choice`).
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
    if self.brokenrefs:
      # for state in expr.walk():
      from .backends.py.graph.walkexpr import walk
      for state in walk(expr):
        if isinstance(state.cursor, backends.Node):
          anchorname = self.brokenrefs.get(state.cursor.id())
          if anchorname is not None:
            parent = state.parent
            if parent is None:
              # This is the trivial cycle a=a.
              state.cursor.forward_to(state.cursor)
            else:
              parent.set_successor(state.realpath[-1], self.anchors[anchorname])
          else:
            state.push()
    return expr

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
    missing =  getattr(ti, 'info', ti).arity - len(args)
    partial_info = self.fsyms.PartApplic if missing > 0 else None
    return self._mknode(
        ti, *map(lambda s: self(s), args), target=self.target
      , partial_info=partial_info
      )

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
    if self.target is not None:
      raise ValueError("cannot rewrite a node to an unboxed value")
    return arg.value

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

