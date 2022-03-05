from .... import backends, icurry, utility
from ....common import T_SETGRD, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from .... import inspect, show
import collections, numbers, operator, types

class Node(object):
  '''A node in a Curry expression graph.'''
  def __new__(*args, **kwds):
    return new_node(*args, **kwds)

  @staticmethod
  def create_partial_applic(ti, *args, target=None, partial_info=None):
    missing =  ti.info.arity - len(args)
    assert missing > 0
    partexpr = Node(ti, *args, partial=True)
    return Node(partial_info, missing, partexpr, target=target)

  def __str__(self):
    return show.show(self)

  def __repr__(self):
    return show.show(self, style='repr')

  def __copy__(self):
    return self.copy()

  def copy(self):
    from .copy import copynode
    return copynode(self)

  def __deepcopy__(self, memo=None):
    from .copy import copygraph
    return copygraph(self, memo=memo)

  def __getitem__(self, path):
    from .indexing import logical_subexpr
    return logical_subexpr(self, path, update_fwd_nodes=True)

  def __iter__(self):
    raise TypeError('Node does not support iteration')

  from .equality import logically_equal as __eq__

  def __hash__(self):
    return hash(id(self)) # for testing

  def __ne__(self, rhs):
    return not (self == rhs)

  def rewrite(self, info, *args, **kwds):
    Node(info, *args, target=self, **kwds)

  def walk(self, path=None):
    '''See walkexpr.walk.'''
    from .walkexpr import walk
    return walk(self, path)


backends.Node.register(Node)

def new_node(cls, info, *args, **kwds):
  '''
  Create or rewrite a node.

  If the keyword 'target' is supplied, then the object will be constructed
  there.  This low-level function is intended for internal use only.  To
  construct an expression, use ``Interpreter.expr``.

  Args:
    info:
      An instance of ``CurryNodeInfo`` or ``InfoTable`` indicating the kind of node to
      create.

    *args:
      The successors.  Each one should be a Node, built-in data object, or
      None.  The value None is not a valid successor, but is used to construct
      cyclic expressions.  These must be replaced before the object is used as
      an expression.  The number of successors must equal info.arity, unless
      partial=True, in which case it should be strictly less.

    target=None:
      Keyword-only argument.  If not None, this specifies an existing Node object
      to rewrite.

    partial=False:
      Indicates whether this constructs a partial application.  If False,
      applying a function to too few arguments will cause ``TypeError`` to be
      raised.

  Returns:
    A ``Node``.
  '''
  if isinstance(info, (types.GeneratorType, collections.Sequence)):
    assert not args
    return new_node(cls, *info, **kwds)
  info = getattr(info, 'info', info)
  bad_length = operator.ge if kwds.get('partial') else operator.ne
  if bad_length(len(args), info.arity):
    raise TypeError(
        'cannot %s %r (arity=%d), with %d arg%s' % (
            ('curry' if kwds.get('partial') else 'construct')
          , info.name
          , info.arity
          , len(args)
          , '' if len(args) == 1 else 's'
          )
      )
  target = kwds.get('target', None)
  target = getattr(target, 'target', target) # accept target=Variable
  self = object.__new__(cls) if target is None else target
  self.info = info
  successors = [getattr(arg, 'rvalue', arg) for arg in args]
  # Run-time typecheck (debug only).
  if info.typecheck is not None and not any(s is None for s in successors):
    info.typecheck(info, *successors)
  assert all(map(inspect.isa_curry_expr_or_none, successors))
  self.successors = successors
  return self
