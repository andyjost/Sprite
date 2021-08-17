from .... import context, icurry, utility
from ....common import T_SETGRD, T_CONSTR, T_VAR, T_FWD, T_CHOICE, T_FUNC, T_CTOR
import collections
import numbers
import operator

__all__ = [
    'InfoTable', 'Node', 'Replacer'
  , 'info_of', 'make_choice', 'make_constraint', 'make_value_bindings'
  , 'replace', 'replace_copy', 'rewrite', 'subexpr', 'tag_of'
  ]

class InfoTable(object):
  '''
  Runtime info for a node.  Every Curry node stores an `InfoTable`` instance,
  which contains instance-independent data.
  '''
  __slots__ = ['name', 'arity', 'tag', '_step', 'show', 'typecheck', 'typedef', 'monadic']
  def __init__(self, name, arity, tag, step, show, typecheck, monadic=False):
    # The node name.  Normally the constructor or function name.
    self.name = name
    # Arity.
    self.arity = arity
    # Node kind tag.
    self.tag = tag
    # The step function.  For functions, this is the function called to perform
    # a computational step at this node.
    self._step = step
    # Implements the show function.
    self.show = show
    # Used in debug mode to verify argument types.  The frontend typechecks
    # generated code, but this is helpful for checking the hand-written code
    # implementing built-in functions.
    self.typecheck = typecheck
    # The type that this constructor belongs to.  This is needed at runtime to
    # implement =:=, when a free variable must be bound to an HNF.  It could be
    # improved to use just a runtime version of the typeinfo.
    self.typedef = None
    # Indicates whether this is an I/O function.
    self.monadic = monadic

  @property
  def step(self):
    # The step function can either be a function or a tuple (f, a, b, ...).  If
    # the latter, then f(a, b, ...) is called to get the actual step function
    # the first time it is accessed.  LazyFunction is a tuple that omits lengthy
    # details from the representation.
    if isinstance(self._step, tuple):
      self._step = self._step[0](*self._step[1:])
    return self._step

  @step.setter
  def step(self, value):
    self._step = value

  def __str__(self):
    return 'Info for "%s"' % self.name

  def __repr__(self):
    return ''.join([
        'InfoTable('
      , ', '.join('%s=%r' % (
            slot, getattr(self, slot)) for slot in self.__slots__
          )
      , ')'
      ])

context.InfoTable.register(InfoTable)

class Node(object):
  '''An expression node.'''
  def __new__(cls, info, *args, **kwds):
    '''
    Create or rewrite a node.

    If the keyword 'target' is supplied, then the object will be constructed
    there.  This low-level function is intended for internal use only.  To
    construct an expression, use ``Interpreter.expr``.

    Parameters:
    -----------
    ``info``
      An instance of ``CurryNodeLabel`` or ``InfoTable`` indicating the kind of node to
      create.
    ``*args``
      The successors.
    ``target=None``
      Keyword-only argument.  If not None, this specifies an existing Node object
      to rewrite.
    ``partial=False``
      Indicates whether this constructs a partial application.  If false,
      applying a function to too few arguments will cause ``TypeError`` to be
      raised.
    '''
    info = getattr(info, 'info', info)
    bad_length = operator.ge if kwds.get('partial') else operator.ne
    if bad_length(len(args), info.arity):
      raise TypeError(
          'cannot %s "%s" (arity=%d), with %d arg%s' % (
              ('curry' if kwds.get('partial') else 'construct')
            , info.name
            , info.arity
            , len(args)
            , '' if len(args) == 1 else 's'
            )
        )
    target = kwds.get('target', None)
    assert target is None or \
           target.info.tag == T_FUNC or \
           (target.info.tag == T_VAR == info.tag)
    self = object.__new__(cls) if target is None else target
    self.info = info
    successors = list(args)
    # Run-time typecheck (debug only).
    if info.typecheck is not None:
      info.typecheck(info, *successors)
    self.successors = successors
    return self

  def __copy__(self):
    return self.copy()

  def copy(self):
    return Node(self.info, *self)

  def __nonzero__(self): # pragma: no cover
    # Without this, nodes without successors are False.
    return True

  @utility.visitation.dispatch.on('i')
  def __getitem__(self, i, *args, **kwds):
    raise RuntimeError('unhandled type: %s' % type(i).__name__)

  @__getitem__.when(str)
  def __getitem__(self, i, *args, **kwds):
    raise RuntimeError('unhandled type: str')

  @__getitem__.when(numbers.Integral)
  def __getitem__(self, i, guards=None, skipguards=True):
    '''Get a successor, skipping over FWD nodes.'''
    self = self.__getitem__(())
    tmp = Node._skipfwd(self.successors[i])
    self.successors[i] = tmp
    if hasattr(tmp, 'info') and tmp.info.tag == T_SETGRD:
      if guards is not None:
        guards.add(int(tmp.successors[0]))
      if skipguards:
        return tmp.successors[1]
    return tmp

  @__getitem__.when(collections.Sequence, no=str)
  def __getitem__(self, path, *args, **kwds):
    if not path:
      return Node._skipfwd(self)
    else:
      for p in path:
        self = self.__getitem__(p, *args, **kwds)
      return self

  @staticmethod
  def getitem_with_guards(node, path):
    return Node.getitem(node, path, skipguards=False)

  @staticmethod
  def getitem(node, i=(), guards=None, skipguards=True):
    '''
    Like ``Node.__getitem__``, but safe when ``node`` is an unboxed value.
    '''
    assert isinstance(i, (int, collections.Sequence))
    if isinstance(node, Node):
      # Free variables don't really have successors.  They should be inspected
      # with special functions such as _Freevar_get_constructors.  This check
      # is a compromise.  It offers some protection against a too-long
      # "path" argument to hnf, for instance.  The lower-level
      # __getitem__ methods still need to accept free variables so that, e.g.,
      # _Freevar_get_constructors can be implemented.
      assert node.info.tag != T_VAR or (not i and i != 0)
      return node.__getitem__(i, guards, skipguards)
    elif not i and i != 0: # empty sequence.
      assert isinstance(node, icurry.ILiteral)
      return node
    else:
      raise TypeError("cannot index into an unboxed value.")

  @staticmethod
  def getitem_and_guards(node, i=(), skipguards=True):
    guards = set()
    item = Node.getitem(node, i, guards, skipguards)
    return item, guards

  @staticmethod
  def _skipfwd(arg):
    '''
    Skips over FWD nodes.  If a chain of FWD nodes is encountered, each one
    will be short-cut to point to the target.  This succeeds for all types, so
    it is safe to pass an unboxed value.
    '''
    if hasattr(arg, 'info') and arg.info.tag == T_FWD:
      target = arg.successors[0] = Node._skipfwd(arg.successors[0])
      return target
    return arg

  @property
  def fwd(self):
    return Node._skipfwd(self)

  def __iter__(self):
    return iter(self.successors)

  def __len__(self):
    return len(self.successors)

  def __eq__(self, rhs):
    if not isinstance(rhs, Node):
      return False
    # Use __getitem__ to compress paths.  Forward nodes do not influence
    # structural equality.
    if self.info != rhs.info:
      return False
    if len(self.successors) != len(rhs.successors):
      return False
    return all(self[i] == rhs[i] for i in xrange(len(self.successors)))

  def __ne__(self, rhs):
    return not (self == rhs)

  def __str__(self):
    return self.info.show(self)

  def _repr_(self):
    yield self.info.name
    for s in self.successors:
      yield repr(s)

  def __repr__(self):
    return '<%s>' % ' '.join(self._repr_())

  def rewrite(self, info, *args, **kwds):
    Node(info, *args, target=self, **kwds)

context.Node.register(Node)

class Replacer(object):
  '''
  Performs replacements in a context, using the alternatives at a target
  position.

  For context C and path p, the target position is C[p].  The Item access self[i]
  returns a copy of C in which C[p] is replaced with C[p][i].  Only nodes along
  the spine are copied.

  The default getter is just getitem, so it will return a successor of the
  target.  This is handy when the target is a choice, since R[1], R[2] will
  return a copy of the expression with the left and right alternatives,
  respectively, in place (note: the zeroth successor is the choice ID).

  A custom getter can be used to construct any replacement desired.

  If a target is supplied, then its subexpressions will be used to construct
  the alternatives.

  Example:
  --------
  Let cxt = [a ? b, c], path = [0], and R = Replacer(cxt, path).  Then R[1] is
  [a, c] and R[2] is [b, c].  Note well that the first successor of a choice is
  the choice ID, so i=1 and i=2 are the left and right alternatives, resp.  In
  each case, a new cons node is created, but c is not copied.

  '''
  def __init__(self, context, path, getter=Node.getitem_with_guards, alternatives=None):
    self.context = context
    self.path = path
    self.target = alternatives # has value after first __getitem__, unless supplied.
    self.getter = getter
    self.guards = set()

  def _a_(self, node, depth=0):
    '''Recurse along the spine.  At the target, call the getter.'''
    if tag_of(node) == T_SETGRD:
      sid = node.successors[0]
      self.guards.add(sid)
      return Node(node.info, sid, self._a_(node.successors[1], depth))
    if depth < len(self.path):
      return Node(*self._b_(node, depth))
    else:
      if self.target is None:
        self.target = node
      return self.getter(self.target, self.index)

  def _b_(self, node, depth):
    '''
    Perform a shallow copy at one node.  Recurse along the spine; reference
    subexpressions not on the spine.
    '''
    if tag_of(node) == T_SETGRD:
      sid = node.successors[0]
      self.guards.add(sid)
      yield node.info
      yield sid
      yield Node(*self._b_(node.successors[1], depth))
    else:
      pos = self.path[depth]
      yield node.info
      for j,_ in enumerate(node.successors):
        if j == pos:
          yield self._a_(Node.getitem(node, j, skipguards=False), depth+1) # spine
        else:
          yield Node.getitem(node, j, skipguards=False) # not spine

  def __getitem__(self, i):
    self.index = i
    return self._a_(self.context)


def info_of(node):
  if isinstance(node, icurry.ILiteral):
    return None
  else:
    return node.info

def make_choice(rts, cid, node, path, generator=None, rewrite=None):
  '''
  Make a choice node with ID ``cid`` whose alternatives are derived by
  replacing ``node[path]`` with the alternatives of choice-rooted
  expression``alternatives``.  If ``alternatives`` is not specified, then
  ``node[path]`` is used.  If ``rewrite`` is supplied, the specified node is
  overwritten.  Otherwise a new node is created.
  '''
  repl = Replacer(node, path, alternatives=generator)
  return Node(rts.prelude._Choice, cid, repl[1], repl[2], target=rewrite)

def make_constraint(constr, node, path, rewrite=None):
  '''
  Make a new constraint object based on ``constr``, which is located at
  node[path].  If ``rewrite`` is supplied, the specified node is overwritten.
  Otherwise a new node is created.
  '''
  repl = Replacer(node, path)
  value = repl[0]
  pair = constr[1]
  return Node(constr.info, value, pair, target=rewrite)

def make_value_bindings(rts, var, values, typedef):
  n = len(values)
  assert n
  if n == 1:
    value = Node(typedef.constructors[0], values[0])
    pair = Node(rts.prelude.Pair, rts.obj_id(var), value)
    return Node(rts.prelude._ValueBinding, value, pair)
  else:
    cid = next(rts.idfactory)
    left = make_value_bindings(rts, var, values[:n//2], typedef)
    right = make_value_bindings(rts, var, values[n//2:], typedef)
    return Node(rts.prelude._Choice, cid, left, right)

def replace(rts, context, path, replacement):
  replacer = Replacer(context, path, lambda _a, _b: replacement)
  replaced = replacer[None]
  context.successors[:] = replaced.successors

def replace_copy(rts, context, path, replacement):
  copy = context.copy()
  replace(rts, copy, path, replacement)
  return copy

def guard_args(rts, guards, node):
  guards = iter(guards)
  last_sid = next(guards)
  for sid in guards:
    node = Node(rts.setfunctions._SetGuard, sid, node)
  yield rts.setfunctions._SetGuard
  yield last_sid
  yield node

def guard(rts, guards, node, target=None):
  return Node(*guard_args(rts, guards, node), target=target)

def subexpr(rts, node, path):
  target, guards = Node.getitem_and_guards(node, path)
  if guards:
    return guard(rts, guards, target)
  else:
    return target

def rewrite(rts, target, info, *args, **kwds):
  guards = kwds.pop('guards', None)
  if guards:
    node = Node(info, *args)
    return guard(rts, guards, node, target=target, **kwds)
  else:
    return Node(info, *args, target=target, **kwds)

def tag_of(node):
  if isinstance(node, icurry.ILiteral):
    return T_CTOR
  else:
    return node.info.tag

