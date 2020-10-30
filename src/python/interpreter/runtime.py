from __future__ import absolute_import
from copy import copy
from .. import icurry
from .. import exceptions
from ..runtime import Fingerprint, LEFT, RIGHT, UNDETERMINED
from ..utility.shared import Shared, compose, DefaultDict
from ..utility import unionfind
from ..utility import visitation
import collections
import itertools
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
    self.ids = set(ids)

class E_STEPLIMIT(BaseException):
  '''Raised when the step limit is reached.'''

class E_CONTINUE(BaseException):
  '''
  Raised when control must break out of the recursive match-eval loop.  This
  occurs when a symbol requiring exceptional handing (e.g., FAIL or CHOICE) was
  placed in a needed position, or when a variable is replaced by a value by
  rewriting the root node.
  '''
  # For example, when reducing g (f (a ? b)), a pull-tab step will replace f
  # with a choice.  Afterwards, this exception is raised to return control to
  # g.

class InfoTable(object):
  '''
  Runtime info for a node.  Every Curry node stores an `InfoTable`` instance,
  which contains instance-independent data.
  '''
  __slots__ = ['name', 'arity', 'tag', '_step', 'show', 'typecheck', 'typedef']
  def __init__(self, name, arity, tag, step, show, typecheck):
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

  @property
  def step(self):
    # The step function can either be a function or a tuple (f, a, b, ...).  If
    # the latter, then f(a, b, ...) is called to get the actual step function
    # the first time it is accessed.
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
           (target.info.tag == T_FREE == info.tag)
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
    tmp = Node._skipfwd(self.successors[i])
    self.successors[i] = tmp
    return tmp

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
      # "path" argument to hnf, for instance.  The lower-level
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

  def __iter__(self):
    return iter(self.successors)

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

Bindings = compose(Shared, compose(DefaultDict, compose(Shared, list)))

class Frame(object):
  '''
  A computation frame.

  One element of the work queue managed by an ``Evaluator``.  Represents an
  expression "activated" for evaluation.
  '''
  def __init__(self, interp=None, expr=None, clone=None):
    if clone is None:
      assert expr is not None
      self.interp = interp
      self.expr = expr
      self.fingerprint = Fingerprint()
      self.constraint_store = Shared(unionfind.UnionFind)
      self.bindings = Bindings()
      self.blocked_by = None
    else:
      assert interp is None or interp is clone.interp
      self.interp = clone.interp
      self.expr = clone.expr if expr is None else expr
      self.fingerprint = copy(clone.fingerprint)
      self.constraint_store = copy(clone.constraint_store)
      self.bindings = copy(clone.bindings)
      # sharing is OK; this is only iterated and replaced.
      self.blocked_by = clone.blocked_by

  def __copy__(self): # pragma: no cover
    return Frame(clone=self)

  def __repr__(self):
    e = self.expr[()]
    xid = get_id(e)
    return '{{hd=%s, fp=%s, cst=%s, bnd=%s, bl=%s}}' % (
        self.expr[()].info.name + ('' if xid is None else '(%s)' % xid)
      , self.fingerprint
      , self.constraint_store.read
      , self.bindings.read
      , self.blocked_by
      )

  def fork(self):
    '''
    Fork a choice-rooted frame into its left and right children.  Yields each
    consistent child.  Recycles ``self``.
    '''
    assert self.expr.info.tag == T_CHOICE
    cid,lhs,rhs = self.expr[()]
    cid = self.constraint_store.read.root(cid)
    if cid in self.bindings.read:
      if not self.update_bindings(cid):
        return
      else:
        cid = self.constraint_store.read.root(cid)
    if cid in self.fingerprint: # Decided, so one child.
      lr = self.fingerprint[cid]
      assert lr in [LEFT,RIGHT]
      self.expr = lhs if lr==LEFT else rhs
      yield self
    else: # Undecided, so two children.
      lchild = Frame(expr=lhs, clone=self)
      lchild.fingerprint.set_left(cid)
      yield lchild
      self.expr = rhs
      self.fingerprint.set_right(cid)
      yield self

  def constrain(self):
    '''
    Process a constraint-rooted frame.  Update the constraint store and discard
    the constraint node.
    '''
    self.expr, (x, y) = self.expr
    if self.bind(x, y):
      yield self

  def update_bindings(self, cid):
    # Collect all variables in the equivalence set of cid.  Clear the bindings
    # as we go.
    seen_ids = set()
    equiv_vars = []
    queue = [cid]
    while queue:
      xid = queue.pop()
      for var in self.bindings.write.pop(xid, []):
        vid = var[0]
        if vid not in seen_ids:
          seen_ids.add(vid)
          equiv_vars.append(var)
          queue.append(vid)
    # Find a variable, the pivot, with a bound generator.
    for pivot in equiv_vars:
      if pivot[1].info.tag == T_CHOICE:
        break
    assert pivot[1].info.tag == T_CHOICE
    # Equate all variables to the pivot.
    for var in equiv_vars:
      if var is not pivot:
        if not self.bind(pivot, var):
          return False
    return True

  def bind(self, x, y):
    assert x.info.tag == y.info.tag
    fp = self.fingerprint
    cs = self.constraint_store
    stack = [(x, y)]
    while stack:
      x, y = stack.pop()
      if x.info.tag == T_CHOICE:
        (x_id, xl, xr), (y_id, yl, yr) = x, y
        x_id, y_id = map(cs.read.root, [x_id, y_id])
        if x_id != y_id:
          x_lr, y_lr = map(fp.get, [x_id, y_id])
          if x_lr != y_lr and UNDETERMINED not in [x_lr, y_lr]:
            return False # inconsistent
          cs.write.unite(x_id, y_id)
          stack.extend([(xl, yl), (xr, yr)])
      else:
        assert x.info.tag == T_FREE
        (x_id, x_gen), (y_id, y_gen) = x, y
        x_id, y_id = map(cs.read.root, [x_id, y_id])
        if x_id != y_id:
          # Whether x/y are NOT bound.
          x_nbnd, y_nbnd = (arg.info.tag == T_CTOR for arg in [x_gen, y_gen])
          if x_nbnd and y_nbnd:
            # Place unbound variables in the binding store.
            bnd = self.bindings.write
            bnd[x_id].write.append(y)
            bnd[y_id].write.append(x)
          else:
            # Continue binding recursively.
            if x_nbnd:
              _clone_generator(y, x)
            elif y_nbnd:
              _clone_generator(x, y)
            stack.append((x_gen, y_gen))
    return True

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
    root = self.constraint_store.read.root
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
    self.queue = collections.deque([Frame(interp, goal)])
    # The number of consecutive blocked frames handled.  If this ever equals
    # the queue length, then the computation fails.
    self.n_consecutive_blocked_seen = 0
    return self

  def D(self):
    '''The dispatch (D) Fair Scheme procedure.'''
    while self.queue:
      frame = self.queue.popleft()
      self.interp.currentframe = frame
      if self._handle_frame_if_blocked(frame):
        continue
      expr = frame.expr
      target = expr[()]
      if isinstance(target, icurry.BuiltinVariant):
        yield target
        continue
      tag = target.info.tag
      if tag == T_CHOICE:
        self.queue.extend(frame.fork())
      elif tag == T_CONSTR:
        self.queue.extend(frame.constrain())
      elif tag == T_FAIL:
        continue # discard
      elif tag == T_FREE:
        vid = get_id(target)
        vid = frame.constraint_store.read.root(vid)
        if vid in frame.fingerprint:
          frame.expr = get_generator(self.interp, target, None)
          self.queue.append(frame)
        else:
          yield target
      elif tag == T_FUNC:
        try:
          S(self.interp, target)
        except E_CONTINUE:
          # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
          self.queue.append(frame)
        except E_RESIDUAL as res:
          self.queue.append(frame.block(blocked_by=res.ids))
        else:
          frame.expr = frame.expr # insert FWD node, if needed.
          self.queue.append(frame)
      elif tag >= T_CTOR:
        try:
          N(self.interp, expr, target)
        except E_CONTINUE:
          # assert expr.info.tag < T_CTOR and expr.info.tag != T_FUNC
          self.queue.append(frame)
        except E_RESIDUAL as res:
          self.queue.append(frame.block(blocked_by=res.ids))
        else:
          target = expr[()]
          if target.info.tag == tag:
            # TODO: check free variables and repeat the call to N if some must
            # be instantiated.
            # UPDATE - I'm not sure that can occur.
            yield target
          else:
            self.queue.append(frame)
      else:
        assert False

  def _handle_frame_if_blocked(self, frame):
    '''
    Process a blocked frame, if applicable.  Returns true if the frame was
    indeed blocked, unless the computation suspends.
    '''
    if frame.blocked:
      self.queue.append(frame)
      if frame.unblock():
        self.n_consecutive_blocked_seen = 0
      else:
        self.n_consecutive_blocked_seen += 1
        if self.n_consecutive_blocked_seen == len(self.queue):
          raise exceptions.EvaluationSuspended()
      return True
    else:
      self.n_consecutive_blocked_seen = 0
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
  def increment(self):
    self._count += 1
    if self._count == self.limit:
      raise E_STEPLIMIT()
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

def nextid(interp):
  '''Generates the next available ID.'''
  return next(interp._idfactory_)

def N(interp, root, target=None, path=None, freevars=None):
  '''The normalize (N) Fair Scheme procedure.'''
  path = [] if path is None else path
  target = root[path] if target is None else target
  assert target.info.tag >= T_CTOR
  freevars = set() if freevars is None else freevars
  if target.info is interp.prelude._PartApplic.info:
    # A partial application is a value even through it may contain a function
    # symbol.  The first successor (# of arguments remaining) is unboxed, so there
    # is nothing to normalize.
    return target, freevars
  path.append(None)
  try:
    for path[-1], succ in enumerate(target):
      while True:
        if isinstance(succ, icurry.BuiltinVariant):
          break
        succ = succ[()]
        tag = succ.info.tag
        if tag == T_FAIL:
          Node(interp.prelude._Failure, target=root)
          raise E_CONTINUE()
        elif tag == T_CHOICE:
          lift_choice(interp, root, path)
          raise E_CONTINUE()
        elif tag == T_CONSTR:
          lift_constr(interp, root, path)
          raise E_CONTINUE()
        elif tag == T_FREE:
          vid = get_id(succ)
          frame = interp.currentframe
          vid = frame.constraint_store.read.root(vid)
          if vid in frame.fingerprint:
            _a,(_b,l,r) = succ
            replacement = l if frame.fingerprint[vid] == LEFT else r
            replace(interp, root, path, replacement)
            raise E_CONTINUE()
          freevars.add(succ)
          break
        elif tag == T_FUNC:
          try:
            S(interp, succ)
          except E_CONTINUE:
            pass
        elif tag >= T_CTOR:
          _,freevars2 = N(interp, root, succ, path, freevars)
          freevars.update(freevars2)
          break
        else:
          assert False
  finally:
    path.pop()
  return target, freevars

def hnf(interp, expr, path, typedef=None):
  assert path
  assert expr.info.tag == T_FUNC
  target = expr[path]
  while True:
    if isinstance(target, icurry.BuiltinVariant):
      return target
    tag = target.info.tag
    if tag == T_FAIL:
      Node(interp.prelude._Failure, target=expr)
      raise E_CONTINUE()
    elif tag == T_CHOICE:
      lift_choice(interp, expr, path)
      raise E_CONTINUE()
    elif tag == T_CONSTR:
      lift_constr(interp, expr, path)
      raise E_CONTINUE()
    elif tag == T_FREE:
      if typedef is None:
        raise E_RESIDUAL([get_id(target)])
      else:
        target = instantiate(interp, expr, path, typedef)
    elif tag == T_FUNC:
      try:
        S(interp, target)
      except E_CONTINUE:
        pass
    elif tag >= T_CTOR:
      return target
    elif tag == T_FWD:
      target = expr[path]
    else:
      assert False

def S(interp, target):
  '''The step (S) Fair Scheme procedure.'''
  interp._stepper(target)

class _Replacer(object):
  '''
  Performs replacements in a context.
  '''
  def __init__(self, context, path, getter=Node.__getitem__):
    self.context = context
    self.path = path
    self.target = None # has value after first __getitem__
    self.getter = getter

  def _a_(self, node, i=0):
    if i < len(self.path):
      return Node(*self._b_(node, i))
    else:
      assert self.target is None or self.target is node
      self.target = node
      return self.getter(node, self.index)

  def _b_(self, node, i):
    pos = self.path[i]
    yield node.info
    for j,_ in enumerate(node.successors):
      if j == pos:
        yield self._a_(node[j], i+1)
      else:
        yield node[j]

  def __getitem__(self, i):
    self.index = i
    return self._a_(self.context)


def lift_choice(interp, source, path):
  '''
  Executes a pull-tab step with source ``source`` and choice-rooted target
  ``source[path]``.

  Parameters:
  -----------
    ``interp``
      The Curry interpreter.

    ``source``
      The pull-tab source.  This node will be overwritten with a choice symbol.

    ``path``
      A sequence of integers giving the path from ``source`` to the target
      choice or constraint.
  '''
  assert source.info.tag < T_CTOR
  assert path
  if source.info is interp.prelude.ensureNotFree.info:
    raise RuntimeError("non-determinism in I/O actions occurred")
  replacer = _Replacer(source, path)
  left = replacer[1]
  right = replacer[2]
  assert replacer.target.info.tag == T_CHOICE
  Node(
      interp.prelude._Choice
    , replacer.target[0] # choice ID
    , left
    , right
    , target=source
    )


def lift_constr(interp, source, path):
  '''
  Executes a pull-tab step with source ``source`` and constraint-rooted target
  ``source[path]``.

  Parameters:
  -----------
    ``interp``
      The Curry interpreter.

    ``source``
      The pull-tab source.  This node will be overwritten with a constraint
      symbol.

    ``path``
      A sequence of integers giving the path from ``source`` to the target
      choice or constraint.
  '''
  assert source.info.tag < T_CTOR
  assert path
  replacer = _Replacer(source, path)
  value = replacer[0]
  assert replacer.target.info.tag == T_CONSTR
  Node(
      replacer.target.info
    , value
    , replacer.target[1] # binding
    , target=source
    )


def instantiate(interp, context, path, typedef):
  '''
  Instantiates a free variable at ``context[path]``.

  Parameters:
  -----------
    ``interp``
      The Curry interpreter.

    ``context``
      The context in which the free variable appears.

    ``path``
      A sequence of integers giving the path in ``context`` to the free
      variable.
  '''
  replacer = _Replacer(
      context, path, lambda node, _: get_generator(interp, node, typedef)
    )
  replaced = replacer[None]
  assert replacer.target.info.tag == T_FREE
  assert context.info == replaced.info
  context.successors[:] = replaced.successors
  return replacer.target[1]

def replace(interp, context, path, replacement):
  replacer = _Replacer(context, path, lambda _a, _b: replacement)
  replaced = replacer[None]
  assert replacer.target.info.tag == T_FREE
  assert context.info == replaced.info
  context.successors[:] = replaced.successors

def _createGenerator(interp, ctors, vid=None, target=None):
  '''
  Creates a generator tree.

  Parameters:
  -----------
    ``interp``
      The Curry interpreter.

    ``ctors``
      The sequence of ``icurry.IConstructor`` objects defining the type to
      generate.

    ``vid``
      The variable ID.  The root choice will be labeled with this ID.  By
      default, a new ID is allocated.

    ``target``
      The node to overwrite with the generator tree.  By default, a new node
      will be allocated.
  '''
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
      , _createGenerator(interp, ctors[:middle])
      , _createGenerator(interp, ctors[middle:])
      , target=target
      )

def _gen_ctors(interp, gen):
  '''Iterate through the constructors of a generator.'''
  queue = [gen]
  while queue:
    gen = queue.pop()
    if gen.info.tag == T_CHOICE:
      queue.extend([gen[2], gen[1]])
    else:
      if gen.info.tag >= T_CTOR:
        yield gen.info
      else:
        # For types with one constructor, the generator is a choice between
        # that constructor and a failure.
        assert gen.info.tag == T_FAIL

def _clone_generator(interp, bound, unbound):
  vid = unbound[0]
  constructors = list(_gen_ctors(bound[1][0]))
  get_generator(interp, unbound, typedef=constructors)

def is_bound(interp, freevar):
  assert freevar.info.tag == T_FREE
  return freevar[1].info is not interp.prelude.Unit.info

def get_generator(interp, freevar, typedef):
  '''
  Get the generator for a free variable.  Instantiates the variable if
  necessary.

  Parameters:
  -----------
  ``interp``
      The interpreter.
  ``freevar``
      The free variable node to instantiate.
  ``typedef``
      A ``TypeDefinition`` that indicates the type to instantiate the variable
      to.  This can also be a list of constructors.  If the free variable has
      already been instantiated, then this can be None.
  '''
  assert freevar.info.tag == T_FREE
  vid = freevar[0]
  if freevar[1].info is interp.prelude.Unit.info:
    constructors = getattr(typedef, 'constructors', typedef)
    instance = _createGenerator(interp, constructors, vid=vid)
    if len(constructors) == 1:
      # Ensure the instance is always choice-rooted.  This is not the most
      # efficient approach, but it simplifies the implementation elsewhere
      # (e.g., see _Replacer._a_).
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

