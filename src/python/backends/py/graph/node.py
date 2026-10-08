from ....common import T_SETGRD, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from ....common import F_INT_TYPE
from ....exceptions import CurryTypeError
from .... import backends, icurry, utility
from .... import inspect, show
from .infotable import InfoTable
import collections.abc, numbers, types

class Node(object):
  '''A node in a Curry expression graph.'''
  # A node holds its info table and its successors, nothing else.  Without an
  # instance dictionary a node is smaller and quicker to create.  The weak
  # reference slot serves the record of result types of the typed builder
  # (typecheck.builder.TypeRecord), which must not outlive the node.
  __slots__ = ('info', 'successors', '__weakref__')

  def __new__(cls, info, *args, target=None, partial_info=None, **kwds):
    if not isinstance(info, InfoTable):
      if isinstance(info, (types.GeneratorType, collections.abc.Sequence)):
        assert not args
        return Node(*info, target=target, partial_info=partial_info, **kwds)
      info = getattr(info, 'info', info)
    target = getattr(target, 'target', target) # accept target=Variable
    if partial_info:
      return Node.create_partial_applic(cls, info, *args, target=target, partial_info=partial_info)
    else:
      return new_node(cls, info, *args, target=target, **kwds)

  @staticmethod
  def create_partial_applic(cls, info, *args, target=None, partial_info=None):
    # new_node checks the count first: too many arguments raise TypeError,
    # as on the C++ backend.
    partexpr = new_node(cls, info, *args, partial=True)
    missing = info.arity - len(args)
    assert missing > 0
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

  def __setitem__(self, i, value):
    # Used by generated code (INodeAssign) to close a cyclic expression built
    # with None placeholders, e.g., a recursive let.  Takes one integer index;
    # the compiler indexes to the parent node first.  Accepts a Variable.
    assert isinstance(i, numbers.Integral)
    value = getattr(value, 'rvalue', value)
    assert inspect.isa_curry_expr_or_none(value)
    self.successors[i] = value

  def successor(self, i):
    return self.successors[i]

  def set_successor(self, i, value):
    self.successors[i] = value

  def __len__(self):
    return len(self.successors)

  def __iter__(self):
    raise TypeError('Node does not support iteration')

  def __eq__(self, rhs):
    # A value that is not a Curry expression is never equal to a node.
    # NotImplemented lets Python answer False for == and True for !=
    # against a foreign object, as its data model expects; the C++ backend
    # answers the same way (py::is_operator in the bindings).
    if not inspect.isa_curry_expr(rhs):
      return NotImplemented
    from .equality import logically_equal
    return logically_equal(self, rhs)

  def __hash__(self):
    return hash(id(self)) # for testing

  def __ne__(self, rhs):
    if not inspect.isa_curry_expr(rhs):
      return NotImplemented
    return not (self == rhs)

  def id(self):
    return id(self)

  def rewrite(self, info, *args, **kwds):
    Node(info, *args, target=self, **kwds)

  def forward_to(self, target):
    from ..currylib.fundamental import Fwd
    self.rewrite(Fwd, target)

  def walk(self, path=None):
    '''See walkexpr.walk.'''
    from .walkexpr import walk
    return walk(self, path)


backends.Node.register(Node)

def new_node(cls, info, *args, target=None, partial=False):
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
  nargs = len(args)
  if (nargs >= info.arity) if partial else (nargs != info.arity):
    raise TypeError(
        'cannot %s %r (arity=%d), with %d arg%s' % (
            ('curry' if partial else 'construct')
          , info.name
          , info.arity
          , nargs
          , '' if nargs == 1 else 's'
          )
      )
  self = object.__new__(cls) if target is None else target
  self.info = info
  successors = [getattr(arg, 'rvalue', arg) for arg in args]
  assert all(map(inspect.isa_curry_expr_or_none, successors))
  if (info.flags & 0xf) == F_INT_TYPE and successors:
    check_int_range(successors[0])
  self.successors = successors
  return self

# The range of Int: 64 bits, as on the C++ backend (issue #105).  An Int
# node never holds a wider integer, so the two backends agree on every
# value.  The message is the one the C++ backend raises
# (backends/cxx/cyrtbindings/graph.cpp).
INT_MIN = -(1 << 63)
INT_MAX = (1 << 63) - 1

def check_int_range(value):
  if type(value) is int and not INT_MIN <= value <= INT_MAX:
    raise CurryTypeError(
        '%d is outside the range of Int (%d to %d)' % (value, INT_MIN, INT_MAX)
      )
