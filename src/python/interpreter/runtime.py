from __future__ import absolute_import
from copy import copy
from .. import icurry
from .. import exceptions
from ..runtime import Fingerprint, LEFT, RIGHT
from ..utility.binding import binding
from ..utility import unionfind
from ..utility import visitation
import collections
import numbers
import operator
import sys
import weakref

T_FAIL   = -6
T_CONSTR = -5
T_FREE   = -4
T_FWD    = -3
T_CHOICE = -2
T_FUNC   = -1
T_CTOR   =  0 # for each type, ctors are numbered starting at zero.

class E_RESIDUAL(BaseException):
  '''Raised when evaluation cannot complete due to uninstantiated free variables.'''
  def __init__(self, ids):
    '''
    Parameters:
    -----------
        ``ids``
            A collection of free variable IDs (ints) blocking evaluation.
    '''
    assert isinstance(ids, set)
    self.ids = ids

class E_STEPLIMIT(BaseException):
  '''Raised when the step limit is reached.'''

class E_SYMBOL(BaseException):
  '''
  Indicates a symbol requiring exceptional handing (i.e., FAIL or CHOICE) was
  encountered in a needed position.
  '''

class InfoTable(object):
  '''
  Runtime info for a node.  Every Curry node stores an `InfoTable`` instance,
  which contains instance-independent data.
  '''
  __slots__ = ['name', 'arity', 'tag', 'step', 'show', 'instantiate', 'typecheck']
  def __init__(self, name, arity, tag, step, show, instantiate, typecheck):
    # The node name.  Normally the constructor or function name.
    self.name = name
    # Arity.
    self.arity = arity
    # Node kind tag.
    self.tag = tag
    # The step function.  For functions, this is the function called to perform
    # a computational step at this node.
    self.step = step
    # Implements the show function.
    self.show = show
    # Implements free variable instantiation for this type.
    self.instantiate = instantiate
    # Used in debug mode to verify argument types.  The frontend typechecks
    # generated code, but this is helpful for checking the hand-written code
    # implementing built-in functions.
    self.typecheck = typecheck

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
  each constructor of a Curry type, and each of the special nodes such as FAIL,
  FWD, and CHOICE is associated with an instance of this object.

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
    if self.info.tag == T_CONSTR:
      return "<curry constraint>"
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
    successors = list(args)
    # Run-time typecheck (debug only).
    if info.typecheck is not None:
      info.typecheck(*successors)
    self.successors = successors
    return self

  def __nonzero__(self): # pragma: no cover
    # Without this, nodes without successors are False.
    return True

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
  def getitem(node, i):
    '''
    Like ``Node.__getitem__``, but safe when ``node`` is an unboxed value.
    '''
    assert isinstance(i, (int, collections.Sequence))
    if isinstance(node, Node):
      # Free variables don't really have successors.  They should be inspected
      # with special functions such as _Freevar_get_constructors.  This check
      # is a compromise.  It offers some protection against a too-long
      # "targetpath" argument to hnf, for instance.  The lower-level
      # __getitem__ methods still need to accept free variables so that, e.g.,
      # _Freevar_get_constructors can be implemented.
      assert node.info.tag != T_FREE or (not i and i != 0)
      return node[i]
    elif not i and i != 0: # empty sequence.
      assert isinstance(node, icurry.BuiltinVariant)
      return node
    else:
      raise TypeError("cannot index into an unboxed value.")

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

  def __len__(self):
    return len(self.successors)

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
  def __init__(self, expr=None, clone=None):
    if clone is None:
      assert expr is not None
      self.expr = expr
      self.fingerprint = Fingerprint()
      self.choices = unionfind.Shared(unionfind.UnionFind)
      self.blocked_by = None
    else:
      self.expr = clone.expr if expr is None else expr
      self.fingerprint = copy(clone.fingerprint)
      self.choices = copy(clone.choices)
      # sharing is OK; this is only iterated and replaced.
      self.blocked_by = clone.blocked_by

  def __copy__(self): # pragma: no cover
    return Frame(clone=self)

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

  @property
  def blocked(self):
    '''Indicates whether the frame is blocked.'''
    return bool(self.blocked_by)

  def block(self, blocked_by):
    '''Block this frame, waiting for any of the free variables.'''
    assert blocked_by
    assert not self.blocked_by
    self.blocked_by = blocked_by
    return self

  def unblock(self):
    '''Try to unblock a blocked frame.'''
    assert self.blocked
    root = self.choices.read.root
    if any(root(x) in self.fingerprint for x in self.blocked_by):
      self.blocked_by = None
      return True
    else:
      return False


class Evaluator(object):
  '''Evaluates Curry expressions.'''
  def __new__(cls, interp, goal):
    self = object.__new__(cls)
    self.interp = interp
    self.queue = [Frame(goal)]
    self.n_blocked = 0
    return self

  def eval(self):
    '''Implements the dispatch (D) Fair Scheme procedure.'''
    # The number of consecutive blocked frames processed unsuccessfully.
    while self.queue:
      frame = self.queue.pop(0)
      if self._process_blocked(frame):
        continue
      expr = frame.expr
      tag = expr.info.tag
      if tag == T_FAIL:
        continue # discard
      elif tag == T_CHOICE:
        self.queue.extend(frame.fork())
      elif tag == T_FWD:
        frame.expr = expr[()]
        self.queue.append(frame)
      elif tag == T_FREE:
        # TODO: check whether to instantiate.
        yield expr
      else:
        try:
          self.interp.nf(expr)
        except E_SYMBOL:
          self.queue.append(frame)
        except E_RESIDUAL as res:
          self.queue.append(frame.block(blocked_by=res.ids))
        else:
          expr = expr[()]
          if expr.info.tag == T_FREE:
            frame.expr = expr
            self.queue.append(frame)
          else:
            assert not isinstance(expr, Node) or expr.info.tag >= T_CTOR
            yield expr

  def _process_blocked(self, frame):
    '''
    Check for and process a blocked frame, if applicable.  Returns true if the
    frame was indeed blocked, unless the computation suspends.
    '''
    if frame.blocked:
      self.queue.append(frame)
      if frame.unblock():
        self.n_blocked = 0
      else:
        self.n_blocked += 1
        if self.n_blocked == len(self.queue):
          raise exceptions.EvaluationSuspended()
      return True
    else:
      self.n_blocked = 0
      return False


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
      interp.nf(expr[()])
    except (E_SYMBOL, E_STEPLIMIT):
      pass


def nextid(interp):
  '''Generates the next available ID.'''
  return next(interp._idfactory_)


def hnf(interp, expr, targetpath=(), ground=None):
  '''
  Head-normalize ``expr`` at ``targetpath``.

  If a needed special symbol is encountered, except for a free variable when
  not grounding, ``expr`` will be overwritten with a symbol and then E_SYMBOL
  raised.

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
  # TODO: examine this check in more detail.
  # ----------------------------------------
  # # In the degenerate case where ``expr`` and ``target`` are the same node,
  # # that node is required to be a function or operation.
  # assert not targetpath or expr.info.tag >= T_FUNC
  # ----------------------------------------
  assert targetpath is () or not hasattr(expr, 'info') or \
      expr.info.tag not in (T_FAIL, T_CONSTR, T_FREE, T_CHOICE)
  target = Node.getitem(expr, targetpath)
  stepcounter = interp.stepcounter
  while stepcounter.check():
    if not isinstance(target, Node):
      # >> FIXME
      # assert isinstance(target, icurry.BuiltinVariant)
      return target
    tag = target.info.tag
    if tag == T_FAIL:
      if targetpath:
        Node(interp.prelude._Failure, target=expr)
      raise E_SYMBOL()
    elif tag == T_CHOICE or tag == T_CONSTR:
      if targetpath:
        pull_tab(interp, expr, targetpath)
      raise E_SYMBOL()
    elif tag == T_FREE:
      if ground is not None:
        # Instantiate the target and replace it in the context of ``expr``.
        # No... just replace the variable in this context.
        pull_tab(interp, expr, targetpath, ground)
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


def nf(interp, expr, targetpath=(), rec=float('inf'), ground=None):
  '''
  Normalize ``expr`` at ``targetpath``.

  Parameters:
  -----------
    ``expr``
        An expression.

    ``targetpath``
        A path to the descendant of ``expr`` to normalize.  If empty, ``expr``
        itself will be normalized.  In that case, its tag must not be T_FAIL,
        T_CHOICE, or T_CONSTR.

    ``rec``
        Recurse at most this many times.  Recursing to *every* successor counts
        as one recursion.  If zero, only the root node is head-normalized.  If
        negative, this function does nothing.  Used mainly for testing and
        debugging.

    ``ground`` # FIXME
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
      assert expr[()].info.tag in [T_FAIL, T_CHOICE, T_CONSTR]
      raise
    if not isinstance(target, Node):
      assert isinstance(target, icurry.BuiltinVariant)
      return
    if target.info.tag == T_FREE:
      assert ground is None
      # if not targetpath:
      #   raise E_SYMBOL()
      return
    assert target.info.tag >= T_CTOR
    if rec > 0:
      for i in xrange(target.info.arity):
        try:
          nf(interp, target, [i], rec-1, ground=ground)
        except E_SYMBOL:
          if targetpath:
            tag = target.info.tag
            if tag == T_FAIL:
              Node(interp.prelude._Failure, target=expr)
            elif tag == T_CHOICE or tag == T_CONSTR:
              pull_tab(interp, expr, targetpath)
            else:
              assert False
          raise


class _PullTabber(object):
  '''
  Constructs the left and right replacements for a pull-tab step.

  ``getLeft`` and ``getRight`` build the left- and righthand sides,
  respectively.  See ``pull_tab``.
  '''
  def __init__(self, interp, source, targetpath, typedef=None):
    self.interp = interp
    self.source = source
    self.targetpath = targetpath
    self.typedef = typedef
    self.target = None

  def _a_(self, node, i=0):
    if i < len(self.targetpath):
      return Node(*self._b_(node, i))
    else:
      assert self.target is None or self.target is node
      self.target = node
      if node.info.tag == T_CONSTR:
        return node[0 if self.left else 1]
      if node.info.tag == T_FREE:
        assert self.typedef is not None
        node = instantiate(self.interp, node, self.typedef)
      assert node.info.tag == T_CHOICE
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
    return self._a_(self.source)

  def getRight(self):
    self.left = False
    return self._a_(self.source)


def pull_tab(interp, source, targetpath, typedef=None):
  '''
  Executes a pull-tab step with source ``source`` and target
  ``source[targetpath]``.

  The target node may be a choice, free variable, or constraint.  If it is a
  free variable, then ``typedef`` will be used to instantiate it.

  Parameters:
  -----------
    ``interp``
      The Curry interpreter.

    ``source``
      The pull-tab source.  This node will be overwritten with a choice or
      constraint symbol.

    ``targetpath``
      A sequence of integers giving the path from ``source`` to the target
      choice or constraint.

    ``typedef``
        If the target is a free variable, this is used to instantiate it.
  '''
  assert targetpath
  pt = _PullTabber(interp, source, targetpath, typedef)
  left = pt.getLeft()
  if source.info is interp.prelude.ensureNotFree.info:
    if pt.target.info.tag in [T_CHOICE, T_FREE]:
      raise RuntimeError("non-determinism in I/O actions occurred")
  if pt.target.info.tag == T_CHOICE:
    right = pt.getRight()
    Node(
        interp.prelude._Choice
      , pt.target[0] # choice ID
      , left
      , right
      , target=source
      )
  else:
    assert pt.target.info.tag == T_CONSTR
    Node(
        pt.target.info
      , left
      , pt.target[1] # constraint
      , target=source
      )


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
    middle = -(-N // 2) # ceiling-divide, e.g., 7 -> 4.
    return Node(
        interp.prelude._Choice
      , vid if vid is not None else nextid(interp)
      , _instantiate(interp, ctors[:middle])
      , _instantiate(interp, ctors[middle:])
      , target=target
      )


def instantiate(interp, freevar, typedef):
  '''
  Instantiate a free variable as the given type.

  Parameters:
  -----------
  ``interp``
      The interpreter.
  ``freevar``
      The free variable node to instantiate.
  ``typedef``
      A ``TypeDefinition`` that indicates the type to instantiate the variable
      to.  This can also be a list of constructors.
  '''
  assert freevar.info.tag == T_FREE
  vid = freevar[0]
  constructors = getattr(typedef, 'constructors', typedef)
  if freevar[1].info is interp.prelude.Unit.info:
    instance = _instantiate(interp, constructors, vid=vid)
    if len(constructors) == 1:
      # Ensure the instance is always choice-rooted.  This is not the most
      # efficient approach, but it simplifies the implementation elsewhere
      # (e.g., see _PullTabber._a_).
      instance = Node(
          interp.prelude._Choice, vid, instance, Node(interp.prelude._Failure)
        )
    Node(freevar.info, vid, instance, target=freevar)
  return freevar[1]


def get_id(arg):
  '''Returns the choice or variable id for a choice or free variable.'''
  if isinstance(arg, Node):
    arg = arg[()]
    if arg.info.tag in [T_FREE, T_CHOICE]:
      cid = arg[0]
      assert cid >= 0
      return cid

