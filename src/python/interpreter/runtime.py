from collections import Sequence
from .. import icurry
from numbers import Integral
from ..visitation import dispatch
import operator
import textwrap

T_FAIL   = -5
T_FREE   = -4
T_FWD    = -3
T_CHOICE = -2
T_FUNC   = -1
T_CTOR   =  0

class E_SYMBOL(BaseException):
  '''
  Indicates a symbol requiring exceptional handing (i.e., FAIL or CHOICE) was
  encountered in a needed position.
  '''
  pass


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
  ``ident``
      The fully-qualified Curry identifier for this kind of node.  An instance
      of ``icurry.IName``.
  ``info``
      An instance of ``InfoTable``.
  '''
  def __init__(self, ident, info):
    self.ident = ident
    self.info = info

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

  # def __iter__(self):
  #   '''Iterate over the successors, skipping FWD nodes.'''
  #   return (self[i] for i in xrange(len(self.successors)))

  @dispatch.on('i')
  def __getitem__(self, i):
    raise RuntimeError('unhandled type: %s' % type(i).__name__)

  @__getitem__.when(str)
  def __getitem__(self, i):
    raise RuntimeError('unhandled type: str')

  @__getitem__.when(Integral)
  def __getitem__(self, i):
    '''Get a successor, skipping over FWD nodes.'''
    self = self[()]
    item = self.successors[i] = Node._skipfwd(self.successors[i])
    return item

  @__getitem__.when(Sequence, no=str)
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

class Evaluator(object):
  '''Evaluates Curry expressions.'''
  def __new__(cls, interp, goal):
    self = object.__new__(cls)
    self.interp = interp
    self.queue = [goal]
    return self

  def eval(self):
    '''Implements the dispatch (D) Fair Scheme procedure.'''
    while self.queue:
      expr = self.queue.pop(0)
      tag = expr.info.tag
      if tag == T_CHOICE:
        self.queue += expr.successors
        continue
      elif tag == T_FAIL:
        continue # discard
      elif tag == T_FWD:
        expr = expr[()]
        self.queue.append(expr)
      else:
        try:
          self.interp.nf(expr)
        except E_SYMBOL:
          self.queue.append(expr)
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

def hnf(interp, expr, targetpath=[]):
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
        itself will be normalized.  In that case, its tag must not be T_FAIL or
        T_CHOICE.

  Returns:
  --------
    The target node.
  '''
  # In the degenerate case where ``expr`` and ``target`` are the same node,
  # that node is required to be a function or operation (i.e., the caller needs
  # to handle special symbols before calling this function).
  assert not targetpath or expr.info.tag >= T_FUNC
  target = expr[targetpath]
  while True:
    if not isinstance(target, Node):
      # assert isinstance(target, icurry.BuiltinVariant)
      return target
    tag = target.info.tag
    if tag == T_FAIL:
      if targetpath:
        Node(interp.ni_Failure, target=expr)
      raise E_SYMBOL()
    elif tag == T_CHOICE:
      if targetpath:
        pull_tab(expr, targetpath)
      raise E_SYMBOL()
    elif tag == T_FREE:
      raise RuntimeError('normalizing a free variable is not implemented')
    elif tag == T_FWD:
      target = target[()]
    elif tag == T_FUNC:
      try:
        interp.step(target)
      except E_SYMBOL:
        pass
    else:
      return target


def nf(interp, expr, targetpath=[], rec=float('inf')):
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
        as one recursion.  If zero, that target is head-normalized.  If
        negative, this function does nothing.  Used mainly for testing and
        debugging.

  Returns:
  --------
    Nothing.
  '''
  if rec >= 0:
    try:
      target = hnf(interp, expr, targetpath)
    except E_SYMBOL:
      assert expr.info.tag in [T_FAIL, T_CHOICE]
      raise
    if not isinstance(target, Node):
      assert isinstance(target, icurry.BuiltinVariant)
      return
    if rec > 0:
      for i in xrange(target.info.arity):
        try:
          nf(interp, target, [i], rec-1)
        except E_SYMBOL:
          if targetpath:
            tag = target.info.tag
            if tag == T_FAIL:
              Node(interp.ni_Failure, target=expr)
            elif tag == T_CHOICE:
              pull_tab(expr, targetpath)
            elif tag == T_FREE:
              raise RuntimeError('instantiating a free variable is not implemented')
            else:
              assert False
          raise


def pull_tab(source, targetpath):
  '''
  Executes a pull-tab step.

  Parameters:
  -----------
    ``source``
      The ancestor, which will be overwritten.

    ``targetpath``
      A sequence of integers giving the path from ``source`` to the target
      (descendent).
  '''
  assert targetpath
  i, = targetpath # temporary
  target = source[i]
  assert target.info.name == 'Choice'
  #
  lsucc = source.successors
  lsucc[i] = target[0]
  lhs = Node(source.info, *lsucc)
  #
  rsucc = source.successors
  rsucc[i] = target[1]
  rhs = Node(source.info, *rsucc)
  #
  Node(target.info, lhs, rhs, target=source)

