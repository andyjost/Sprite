from .. import icurry
from ..visitation import dispatch
import textwrap

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

  def __repr__(self):
    return ''.join([
        'InfoTable('
      , ', '.join('%s=%s' % (
            slot, getattr(self, slot)) for slot in self.__slots__
          )
      , ')'
      ])


class TypeInfo(object):
  '''Compile-time type info.'''
  def __init__(self, ident, info):
    self.ident = ident
    self.info = info

  def _check_call(self, *args):
    if len(args) != self.info.arity:
      raise TypeError(
          'cannot construct "%s" (arity=%d), with %d args'
              % (self.info.name, self.info.arity, len(args))
        )

  def __call__(self, *args):
    '''Constructs an object of this type.'''
    self._check_call(*args)
    return Node(self.info, *args)

  def __str__(self):
    return 'TypeInfo for %s' % self.ident


class Node(object):
  '''An expression node.'''
  def __new__(cls, info, *args):
    self = object.__new__(cls)
    self.rewrite(info, *args)
    return self

  def rewrite(self, info, *args):
    self.info = info
    self.successors = list(args)

  def __getitem__(self, i):
    '''Get a successor, skipping over FWD nodes.'''
    assert self.info.tag != T_FWD
    x = self.successors[i]
    while hasattr(x, 'info') and x.info.tag == T_FWD:
      x = x[0]
    return x

  def __eq__(self, rhs):
    return self.info == rhs.info and self.successors == rhs.successors

  def __ne__(self, rhs):
    return not (self == rhs)

  def __str__(self):
    return self.info.show(self)

  def __repr__(self):
    return '<%s %s>' % (self.info.name, self.successors)

  # An alias for ``Node.write``.  This gives a consistent syntax for node
  # creation and rewriting.  For example, ``node(*args)`` creates a node and
  # ``lhs.node(*args)`` rewrites ``lhs``.
  node = rewrite

# An alias for node creation.
node = Node


class Evaluator(object):
  '''
  Curry expression evaluator.

  Implements the dispatch (D) Fair Scheme procedure.
  '''
  def __new__(cls, interpreter, goal):
    self = object.__new__(cls)
    self.interpreter = interpreter
    self.queue = [goal]
    return self

  def run(self):
    while self.queue:
      expr = self.queue.pop(0)
      is_value = False
      if not isinstance(expr, Node):
        yield expr
      elif expr.info.tag == T_CHOICE:
        self.queue += expr.successors
        continue
      elif expr.info.tag == T_FAIL:
        continue # discard
      else:
        try:
          is_value = expr.info.step(expr)
        except E_SYMBOL:
          self.queue.append(expr)
        else:
          if is_value:
            yield expr
          else:
            self.queue.append(expr)


def ctor_step(interpreter):
  def step_function(ctor):
    '''
    Step function for constructors.  Corresponds to applying the Fair Scheme N
    procedure.
    '''
    is_value = True
    for i,expr in enumerate(ctor.successors):
      if not isinstance(expr, Node):
        assert isinstance(expr, icurry.BuiltinVariant)
        continue
      tag = expr.info.tag
      if tag == T_CHOICE:
        pull_tab(ctor, [i])
        return False
      elif tag == T_FAIL:
        ctor.rewrite(interpreter.ti_Failure)
        return False
      else:
        is_value = is_value and expr.info.step(expr)
    return is_value
  return step_function


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
  source.rewrite(target.info, lhs, rhs)


def hnf(interpreter):
  def hnf(lhs, target):
    '''
    Attempts to reduce the target node to head-normal form.

    If a needed failure or choice symbol is encountered, the lhs is overwritten
    with failure or via a pull-tab, respectively, and E_SYMBOL is raised.
    '''
    while True:
      tag = target.info.tag
      if tag == T_FAIL:
        return lhs.rewrite(interpreter.ti_Failure)
        raise E_SYMBOL
      elif tag == T_CHOICE:
        pull_tab(lhs, target)
        raise E_SYMBOL
      elif tag == T_FUNC:
        try:
          target.info.step(target)
        except E_SYMBOL:
          pass
      else:
        assert tag != T_FWD
        return target
  return hnf
