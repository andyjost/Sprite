from .. import icurry
from ..visitation import dispatch
import textwrap
from collections import Sequence
from numbers import Integral

T_FAIL   = -4
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
  '''The runtime data stored in the ``info`` slot of every node.'''
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


class Node(object):
  '''An expression node.'''
  def __new__(cls, info, *args):
    self = object.__new__(cls)
    self.rewrite(info, *args)
    return self

  def rewrite(self, info, *args):
    self.info = info
    self.successors = list(args)

  @dispatch.on('i')
  def __getitem__(self, i):
    raise RuntimeError('unhandled type')

  @__getitem__.when(Integral)
  def __getitem__(self, i):
    '''Get a successor, skipping over FWD nodes.'''
    self = self[()]
    obj = self.successors[i]
    while hasattr(obj, 'info') and obj.info.tag == T_FWD:
      obj = obj.successors[0]
    self.successors[i] = obj
    return obj

  @__getitem__.when(Sequence)
  def __getitem__(self, path):
    if not path:
      # Returns self.  If self if a FWD node, skips to a returns the target.
      if self.info.tag == T_FWD:
        self_ = self.successors[0]
        while hasattr(self_, 'info') and self_.info.tag == T_FWD:
          self_ = self_.successors[0]
        self.successors[0] = self_
        return self_
      else:
        return self
    else:
      for p in path:
        self = self[p]
      return self

  def __eq__(self, rhs):
    return self.info == rhs.info and self.successors == rhs.successors

  def __ne__(self, rhs):
    return not (self == rhs)

  def __str__(self):
    return self.info.show(self)

  def __repr__(self):
    return '<%s %s>' % (self.info.name, self.successors)

  # An alias for ``Node.rewrite``.  This gives a consistent syntax for node
  # creation and rewriting.  For example, ``node(*args)`` creates a node and
  # ``lhs.node(*args)`` rewrites ``lhs``.  This simplifies the code generator.
  node = rewrite

# An alias for node creation.
node = Node


class Evaluator(object):
  '''Evaluates Curry expressions.'''
  def __new__(cls, interpreter, goal):
    self = object.__new__(cls)
    self.interpreter = interpreter
    self.queue = [goal]
    return self

  def eval(self):
    '''Implements the dispatch (D) Fair Scheme procedure.'''
    while self.queue:
      expr = self.queue.pop(0)
      if not isinstance(expr, Node):
        assert isinstance(expr, icurry.BuiltinVariant)
        yield expr
      tag = expr.info.tag
      if tag == T_CHOICE:
        self.queue += expr.successors
        continue
      elif tag == T_FAIL:
        continue # discard
      elif tag == T_FWD:
        target = target[()]
      else:
        try:
          yield self.interpreter.nf(expr)
        except E_SYMBOL:
          self.queue.append(expr)


def hnf(interpreter, expr, targetpath=[]):
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
      assert isinstance(target, icurry.BuiltinVariant)
      return target
    tag = target.info.tag
    if tag == T_FAIL:
      if targetpath:
        expr.rewrite(interpreter.ti_Failure)
      raise E_SYMBOL()
    elif tag == T_CHOICE:
      if targetpath:
        pull_tab(expr, targetpath)
      raise E_SYMBOL()
    elif tag == T_FWD:
      target = target[()]
    elif tag == T_FUNC:
      try:
        target.info.step(target)
      except E_SYMBOL:
        pass
    else:
      return target


def nf(interpreter, expr, targetpath=[], rec=float('inf')):
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
      target = hnf(interpreter, expr, targetpath)
    except E_SYMBOL:
      assert expr.info.tag in [T_FAIL, T_CHOICE]
      raise
    if not isinstance(target, Node):
      assert isinstance(target, icurry.BuiltinVariant)
      return
    if rec > 0:
      for i in xrange(target.info.arity):
        try:
          nf(interpreter, target, [i], rec-1)
        except E_SYMBOL:
          if targetpath:
            tag = target.info.tag
            if tag == T_FAIL:
              expr.rewrite(interpreter.ti_Failure)
            elif tag == T_CHOICE:
              pull_tab(expr, targetpath)
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
  try:
    assert targetpath
  except:
    breakpoint()
    raise
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
  source.rewrite(target.info, lhs, rhs)

