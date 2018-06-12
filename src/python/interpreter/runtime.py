from __future__ import absolute_import
from .. import icurry
from .. import visitation
import collections
import numbers
import operator
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

class E_INCONSISTENT(BaseException):
  '''Indicates an inconsistency occurred.'''


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
    try:
      return getattr(self.info.step, 'source')
    except AttributeError:
      raise AttributeError(
          'no implementation code available for %s' % self.ident
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

LEFT = 0
RIGHT = 1

class Evaluator(object):
  '''Evaluates Curry expressions.'''
  def __new__(cls, interp, goal):
    self = object.__new__(cls)
    self.interp = interp
    self.queue = [Evaluator.Frame(goal)]
    return self

  class Frame(object):
    def __init__(self, expr, fingerprint=None, binding=None):
      self.expr = expr
      self.fingerprint = {} if fingerprint is None else dict(fingerprint)
      if binding:
        cid,lr = binding
        if self.fingerprint.get(cid, lr) != lr:
          raise E_INCONSISTENT()
        self.fingerprint[cid] = lr

  def eval(self):
    '''Implements the dispatch (D) Fair Scheme procedure.'''
    Frame = Evaluator.Frame
    while self.queue:
      frame = self.queue.pop(0)
      expr = frame.expr
      tag = expr.info.tag
      if tag == T_CHOICE:
        cid = expr[0]
        for root,lr in zip(expr.successors[1:], [LEFT,RIGHT]):
          try:
            frame_ = Frame(root, frame.fingerprint, (cid,lr))
          except E_INCONSISTENT:
            pass
          else:
            self.queue.append(frame_)
        continue
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


def get_stepper(interp):
  '''
  Returns a function to apply steps, according to the interp
  configuration.
  '''
  if interp.flags['trace']:
    def step(target):
      print 'S <<<', str(target)
      try:
        target.info.step(target)
      finally:
        print 'S >>>', str(target)
  else:
    def step(target):
      target.info.step(target)
  return step


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
        This can be None or an instance of TypeDefinition.  If grounding, a
        free variable occuring at the head will be instantiated to the given
        type.

  Returns:
  --------
    The target node.
  '''
  # In the degenerate case where ``expr`` and ``target`` are the same node,
  # that node is required to be a function or operation.
  # assert not targetpath or expr.info.tag >= T_FUNC
  target = expr[targetpath]
  while True:
    if not isinstance(target, Node):
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
        instantiate(interp, target, ground)
      else:
        return target
    elif tag == T_FWD:
      target = target[()]
    elif tag == T_FUNC:
      try:
        interp.step(target)
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

class PullTabBuilder(object):
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
  '''
  def __init__(self, source, targetpath):
    self.source = source
    self.targetpath = targetpath
    self.cid = None

  def _a_(self, node, i):
    if i < len(self.targetpath):
      return Node(*self._b_(node, i))
    else:
      assert node.info.name == "_Choice"
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

def pull_tab(interp, source, targetpath):
  '''
  Executes a pull-tab step.

  Parameters:
  -----------
    ``source``
      The pull-tab source.  This node will be overwritten with a choice symbol.

    ``targetpath``
      A sequence of integers giving the path from ``source`` to the target
      (i.e., choice symbol).
  '''
  if source.info == interp.prelude.ensureNotFree.info:
    raise RuntimeError("non-determinism occurred in I/O actions")
  assert targetpath
  pt = PullTabBuilder(source, targetpath)
  left, right = pt.getLeft(), pt.getRight()
  assert pt.cid >= 0
  Node(
      interp.prelude._Choice
    , pt.cid
    , left
    , right
    , target=source
    )


def _instantiate(interp, ctors, cid=None, target=None):
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
    middle = -(-N // 2)
    return Node(
        interp.prelude._Choice
      , cid if cid is not None else nextid(interp)
      , _instantiate(interp, ctors[:middle])
      , _instantiate(interp, ctors[middle:])
      , target=target
      )

def instantiate(interp, freevar, typedef):
  '''Instantiate a free variable as the given type.'''
  assert freevar.info.tag == T_FREE
  cid = freevar[0]
  _instantiate(interp, typedef.constructors, cid=cid, target=freevar)

