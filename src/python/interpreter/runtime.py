from __future__ import absolute_import
from copy import copy
from .. import icurry
from ..runtime import Fingerprint, LEFT, RIGHT
from ..utility.binding import binding
from ..utility import visitation
import collections
import numbers
import operator
import sys
import weakref

T_FAIL   = -5
T_FREE   = -4
T_FWD    = -3
T_CHOICE = -2
T_FUNC   = -1
T_CTOR   =  0 # for each type, ctors are numbered starting at zero.

class E_SYMBOL(BaseException):
  '''
  Indicates a symbol requiring exceptional handing (i.e., FAIL or CHOICE) was
  encountered in a needed position.
  '''

class E_STEPLIMIT(BaseException):
  '''Raised when the step limit is reached.'''

class InfoTable(object):
  '''
  Runtime info for a node.  Every Curry node stores an `InfoTable`` instance,
  which contains instance-independent data.
  '''
  __slots__ = ['name', 'arity', 'tag', 'step', 'show']
  def __init__(self, name, arity, tag, step, show):
    self.name = name
    self.arity = arity
    self.tag = tag
    self.step = step
    self.show = show

  def __str__(self):
    return 'Info for "%s"' % self.name

  def __repr__(self):
    return ''.join([
        'InfoTable('
      , ', '.join('%s=%s' % (
            slot, getattr(self, slot)) for slot in self.__slots__
          )
      , ')'
      ])


class NodeInfo(object):
  '''
  Compile-time node info.

  Each kind of node has its own compiler-generated info.  Each Curry function,
  each constructor of a Curry type, and each of the special nodes FAIL, FWD,
  and CHOICE is associated with an instance of this object.

  Attributes:
  -----------
  ``icurry``
      The ICurry source of this Node.
  ``ident``
      The fully-qualified Curry identifier for this kind of node.  An instance
      of ``icurry.IName``.
  ``info``
      An instance of ``InfoTable``.
  '''
  def __init__(self, icurry, info):
    self.icurry = icurry
    self.info = info

  @property
  def ident(self):
    return self.icurry.ident

  # TODO: add getsource to get the Curry source.  It will require an
  # enhancement to CMC and maybe FlatCurry to generate source range
  # annotations.

  def getimpl(self):
    '''Returns the implementation code of the step function, if available.'''
    step = self.info.step
    try:
      return getattr(step, 'source')
    except AttributeError:
      raise ValueError(
          'no implementation code available for "%s"' % self.ident
        )

  def __str__(self):
    return self.ident

  def __repr__(self):
    if self.info.tag >= T_CTOR:
      return "<curry constructor '%s'>" % self.ident
    if self.info.tag == T_FUNC:
      return "<curry function '%s'>" % self.ident
    if self.info.tag == T_CHOICE:
      return "<curry choice>"
    if self.info.tag == T_FWD:
      return "<curry forward node>"
    if self.info.tag == T_FAIL:
      return "<curry failure>"
    if self.info.tag == T_FREE:
      return "<curry free variable>"
    return "<invalid curry node>"


class TypeDefinition(object):
  def __init__(self, ident, constructors):
    self.ident = ident
    self.constructors = constructors
    for ctor in self.constructors:
      ctor.typedef = weakref.ref(self)
  def __repr__(self):
    return "<curry type %s>" % self.ident


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
      An instance of ``NodeInfo`` or ``InfoTable`` indicating the kind of node to
      create.
    ``*args``
      The successors.
    ``target=None``
      Keyword-only argument.  If not None, this specifies an existing Node object
      to rewrite.
    ``partial=False``
      Indicates whether this constructs a partial application.
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
    self = object.__new__(cls) if target is None else target
    self.info = info
    self.successors = list(args)
    return self

  @visitation.dispatch.on('i')
  def __getitem__(self, i):
    raise RuntimeError('unhandled type: %s' % type(i).__name__)

  @__getitem__.when(str)
  def __getitem__(self, i):
    raise RuntimeError('unhandled type: str')

  @__getitem__.when(numbers.Integral)
  def __getitem__(self, i):
    '''Get a successor, skipping over FWD nodes.'''
    self = self[()]
    item = self.successors[i] = Node._skipfwd(self.successors[i])
    return item

  @__getitem__.when(collections.Sequence, no=str)
  def __getitem__(self, path):
    if not path:
      return Node._skipfwd(self)
    else:
      for p in path:
        self = self[p]
      return self

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

  def __eq__(self, rhs):
    if not isinstance(rhs, Node):
      return False
    return self.info == rhs.info and self.successors == rhs.successors

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

  # Rewrite this node. This gives a consistent syntax for node creation and
  # rewriting.  For example, ``Node(*args)`` creates a node and
  # ``lhs.Node(*args)`` rewrites ``lhs``.  This simplifies the code generator.
  def Node(self, info, *args):
    Node(info, *args, target=self)


class Frame(object):
  '''
  A computation frame.

  One element of the work queue managed by an ``Evaluator``.  Represents an
  expression "activated" for evaluation.
  '''
  def __init__(self, expr, arg=None):
    self.expr = expr
    if arg is None:
      self.fingerprint = Fingerprint()
      self.constraints = Constraints()
    else:
      self.fingerprint = copy(arg.fingerprint)
      self.constraints = copy(arg.constraints)

  def fork(self):
    '''
    Fork a choice-rooted frame into its left and right children.  Yields each
    consistent child.  Recycles ``self``.
    '''
    assert self.expr.info.tag == T_CHOICE
    cid,lhs,rhs = self.expr
    if cid in self.fingerprint: # Decided, so one child.
      lr = self.fingerprint[cid]
      assert lr in [LEFT,RIGHT]
      self.expr = lhs if lr==LEFT else rhs
      yield self
    else: # Undecided, so two children.
      lchild = Frame(lhs, self)
      lchild.fingerprint.set_left(cid)
      yield lchild
      self.expr = rhs
      self.fingerprint.set_right(cid)
      yield self


class Evaluator(object):
  '''Evaluates Curry expressions.'''
  def __new__(cls, interp, goal):
    self = object.__new__(cls)
    self.interp = interp
    self.queue = [Frame(goal)]
    return self

  def eval(self):
    '''Implements the dispatch (D) Fair Scheme procedure.'''
    while self.queue:
      frame = self.queue.pop(0)
      expr = frame.expr
      tag = expr.info.tag
      if tag == T_CHOICE:
        self.queue.extend(frame.fork())
      elif tag == T_FAIL:
        continue # discard
      elif tag == T_FWD:
        frame.expr = expr[()]
        self.queue.append(frame)
      else:
        try:
          self.interp.nf(expr)
        except E_SYMBOL:
          self.queue.append(frame)
        else:
          yield expr[()]


class StepCounter(object):
  '''
  Counts the number of steps taken.  If a limit is provided, raises E_STEPLIMIT
  when the limit is reached.
  '''
  def __init__(self, limit=None):
    assert limit > 0 or limit is None
    self._limit = -1 if limit is None else limit
    self.reset()
  @property
  def count(self):
    return self._count
  @property
  def limit(self):
    return self._limit
  def check(self):
    if self._count == self.limit:
      raise E_STEPLIMIT()
    return True
  def increment(self):
    self._count += 1
  def reset(self):
    self._count = 0


def get_stepper(interp):
  '''
  Returns a function to apply steps, according to the interp
  configuration.
  '''
  if interp.flags['trace']:
    def step(target): # pragma: no cover
      print 'S <<<', str(target)
      try:
        target.info.step(target)
        interp.stepcounter.increment()
      finally:
        print 'S >>>', str(target)
  else:
    def step(target):
      target.info.step(target)
      interp.stepcounter.increment()
  return step


def step(interp, expr, num=1):
  '''
  Takes the specified number of steps at the head of the given expression.
  '''
  with binding(interp.__dict__, 'stepcounter', StepCounter(limit=num)):
    try:
      interp.nf(expr)
    except (E_SYMBOL, E_STEPLIMIT):
      pass


def nextid(interp):
  '''Generates the next available ID.'''
  return next(interp._idfactory_)


def hnf(interp, expr, targetpath=[], ground=None):
  '''
  Head-normalize ``expr`` at ``targetpath``.

  If a needed failure or choice symbol is encountered, ``expr`` is overwritten
  with a failure or choice, respectively, and then E_SYMBOL is raised.

  Parameters:
  -----------
    ``expr``
        An expression.

    ``targetpath``
        A path to the descendant of ``expr`` to normalize.  If empty, ``expr``
        itself will be normalized.  In that case, its tag must not be T_FAIL,
        T_FREE, or T_CHOICE.

    ``ground``
        Indicates whether to normalize to grounded head-normal form.  A free
        variable at the head will be instantiated if and only if this is true.
        This can be None or an instance of TypeDefinition.  If grounding, and
        if the target position is a free variable, it will be instantiated as
        this type.

  Returns:
  --------
    The target node.
  '''
  # In the degenerate case where ``expr`` and ``target`` are the same node,
  # that node is required to be a function or operation.
  # assert not targetpath or expr.info.tag >= T_FUNC
  target = expr[targetpath]
  stepcounter = interp.stepcounter
  while stepcounter.check():
    if not isinstance(target, Node):
      # >> FIXME
      # assert isinstance(target, icurry.BuiltinVariant) # or free
      return target
    tag = target.info.tag
    if tag == T_FAIL:
      if targetpath:
        Node(interp.prelude._Failure, target=expr)
      raise E_SYMBOL()
    elif tag == T_CHOICE:
      if targetpath:
        pull_tab(interp, expr, targetpath)
      raise E_SYMBOL()
    elif tag == T_FREE:
      if ground:
        # Instantiate the target and replace it in the context of ``expr``.
        pull_tab(interp, expr, targetpath, typedef=ground)
        raise E_SYMBOL()
      else:
        return target
    elif tag == T_FWD:
      target = target[()]
    elif tag == T_FUNC:
      try:
        interp._step(target)
      except E_SYMBOL:
        pass
    else:
      return target


def nf(interp, expr, targetpath=[], rec=float('inf'), ground=False):
  '''
  Normalize ``expr`` at ``targetpath``.

  Parameters:
  -----------
    ``expr``
        An expression.

    ``targetpath``
        A path to the descendant of ``expr`` to normalize.  If empty, ``expr``
        itself will be normalized.  In that case, its tag must not be T_FAIL or
        T_CHOICE.

    ``rec``
        Recurse at most this many times.  Recursing to *every* successor counts
        as one recursion.  If zero, only the root node is head-normalized.  If
        negative, this function does nothing.  Used mainly for testing and
        debugging.

    ``ground``
        Indicates whether to normalize to ground normal form.  Needed free
        variables will be instantiated if and only if this is true.

  Returns:
  --------
    Nothing.
  '''
  if rec >= 0:
    try:
      target = hnf(interp, expr, targetpath, ground=ground)
    except E_SYMBOL:
      assert expr[()].info.tag in [T_FAIL, T_CHOICE]
      raise
    if not isinstance(target, Node):
      assert isinstance(target, icurry.BuiltinVariant)
      return
    if rec > 0:
      for i in xrange(target.info.arity):
        try:
          nf(interp, target, [i], rec-1, ground=ground)
        except E_SYMBOL:
          if targetpath:
            tag = target.info.tag
            if tag == T_FAIL:
              Node(interp.prelude._Failure, target=expr)
            elif tag == T_CHOICE:
              pull_tab(interp, expr, targetpath)
            else:
              assert False
          raise


class _PullTabber(object):
  '''
  Constructs the left and right replacements for a pull-tab step.

  ``getLeft`` and ``getRight`` build the left- and righthand sides,
  respectively.  After calling either, the ``cid`` stores the choice ID.

  Parameters:
    ``source``
        The pull-tab source node.
    ``targetpath``
        The path (sequence of integers) from source to target (i.e.,
        choice-labeled node).
    ``typedef``
        If the target is a free variable, this is used to instantiate it.
  '''
  def __init__(self, interp, source, targetpath, typedef=None):
    self.interp = interp
    self.source = source
    self.targetpath = targetpath
    self.typedef = typedef
    self.cid = None

  def _a_(self, node, i):
    if i < len(self.targetpath):
      return Node(*self._b_(node, i))
    else:
      if node.info.tag == T_FREE:
        assert self.typedef is not None
        node = instantiate(self.interp, node, self.typedef)
      assert node.info.tag == T_CHOICE
      assert self.cid is None or self.cid == node[0]
      self.cid = node[0]
      return node[1 if self.left else 2]

  def _b_(self, node, i):
    pos = self.targetpath[i]
    yield node.info
    for j,_ in enumerate(node.successors):
      if j == pos:
        yield self._a_(node[j], i+1)
      else:
        yield node[j]

  def getLeft(self):
    self.left = True
    return self._a_(self.source, 0)

  def getRight(self):
    self.left = False
    return self._a_(self.source, 0)


def pull_tab(interp, source, targetpath, typedef=None):
  '''
  Executes a pull-tab step with source ``source`` and target
  ``source[targetpath]``.

  If the target is a free variable, then ``typedef`` will be used to
  instantiate it.

  Parameters:
  -----------
    ``source``
      The pull-tab source.  This node will be overwritten with a choice symbol.

    ``targetpath``
      A sequence of integers giving the path from ``source`` to the target
      (i.e., choice symbol).

  '''
  if source.info is interp.prelude.ensureNotFree.info:
    raise RuntimeError("non-determinism occurred in I/O actions")
  assert targetpath
  pt = _PullTabber(interp, source, targetpath, typedef)
  left, right = pt.getLeft(), pt.getRight()
  assert pt.cid >= 0
  Node(interp.prelude._Choice, pt.cid, left, right, target=source)


def _instantiate(interp, ctors, vid=None, target=None):
  N = len(ctors)
  assert N
  if N == 1:
    ctor, = ctors
    unknown = interp.prelude.unknown
    return Node(
        ctor
      , *[Node(unknown) for _ in xrange(ctor.info.arity)]
      , target=target
      )
  else:
    middle = -(-N // 2) # e.g., 7 -> 4.
    return Node(
        interp.prelude._Choice
      , vid if vid is not None else nextid(interp)
      , _instantiate(interp, ctors[:middle])
      , _instantiate(interp, ctors[middle:])
      , target=target
      )


def instantiate(interp, freevar, typedef):
  '''Instantiate a free variable as the given type.'''
  assert freevar.info.tag == T_FREE
  vid = freevar[0]
  if freevar[1].info is interp.prelude.Unit.info:
    instance = _instantiate(
        interp, typedef.constructors, vid=vid #, target=freevar
      )
    if len(typedef.constructors) == 1:
      # Ensure the instance is always choice-rooted.  This is not the most
      # efficient thing to do, but it simplifies the implementation elsewhere
      # (e.g., see _PullTabber._a_).
      instance = Node(
          interp.prelude._Choice, vid, instance, Node(interp.prelude._Failure)
        )
    Node(freevar.info, vid, instance, target=freevar)
  return freevar[1]


class Shared(object):
  '''Manages an object with copy-on-write semantics.'''
  def __init__(self, ty, obj=None):
    self.ty = ty
    if obj is None:
      self.obj = ty()
      assert self.unique
    else:
      self.obj = obj
  def __copy__(self):
    return Shared(self.ty, self.obj) # sharing copy
  @property
  def read(self):
    return self.obj
  @property
  def write(self):
    if not self.unique:
      self.obj = self.ty(self.obj) # copy for write
    assert self.unique
    return self.obj
  @property
  def refcnt(self):
    return sys.getrefcount(self.obj) - 1
  @property
  def unique(self):
    return self.refcnt == 1
  def __repr__(self):
    return 'Shared(refcnt=%s, %s)' % (self.refcnt, self.obj)
  # Read-only container methods, for convenience.
  def __contains__(self, key):
    return key in self.obj
  def __len__(self):
    return len(self.obj)
  def __getitem__(self, key):
    return self.obj[key]


class ChoiceStore(object):
  '''Weighted quick-union with path compression.'''
  def __init__(self, obj=None):
    if obj is None:
      self.choices = Shared(dict)
      self.size = Shared(dict)
    else:
      self.choices = obj.choices.__copy__()
      self.size = obj.size.__copy__()
  def __copy__(self):
    return ChoiceStore(self)
  def __contains__(self, i):
    return i in self.choices.read
  def __getitem__(self, i):
    return self.choices.read.setdefault(i, i)
  def __setitem__(self, i, j):
    self.choices.write[i] = j
  def root(self, i):
    while i != self[i]:
      self[i] = self[self[i]]
      i = self[i]
    return i
  def find(self, p, q):
    return self.root(p) == self.root(q)
  def unite(self, p, q):
    i = self.root(p)
    j = self.root(q)
    if self.size.read.setdefault(i,1) < self.size.read.setdefault(j,1):
      self.choices.write[i] = j
      self.size.write[j] += self.size[i]
    else:
      self.choices.write[j] = i
      self.size.write[i] += self.size[j]
  def __repr__(self):
    return repr(self.choices.read)


class Constraints(object):
  def __init__(self, arg=None):
    if arg is None:
      # defaultdict = collections.defaultdict
      # # Holds the variable bindings.  There are two types: lazy and normal.  A
      # # lazy binding is between a variable and an unevaluated expression, used
      # # to implement =:<= for functional patterns.  A normal binding is between
      # # two free variables, used to implement =:=.  These bindings imply
      # # additional bindings between successor variables.  For example, if x_0
      # # :=: x_1 for two list variables, then after annotating x_0 = ([] ?_0
      # # (x_2:x_3)) and x_1 = ([] ?_1 (x_4:x_5)), we have two new bindings x_2
      # # :=: x_4 and x_3 :=: x_5.
      # self.vars = Shared(lambda: defaultdict(lambda: Shared(list)))
      self.choices = Shared(ChoiceStore)
    else:
      # self.vars = arg.vars
      self.choices = copy(arg.choices)

  def __copy__(self):
    return Constraints(self)

  # def uniteVars(self, node_from, node_to, is_lazy):
  #   store = self.vars.write
  #   cid = node_from[0]
  #   store[cid].write.append((node_from, node_to, is_lazy))
  #   if not is_lazy:
  #     cid = node_to[0]
  #     store[cid].write.append((node_to, node_from, is_lazy))

  # def uniteChoices(self, i, j):
  #   if not self.choices.read.find(i, j):
  #     self.choices.write.unite(i, j)
