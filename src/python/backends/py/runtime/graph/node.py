from ..... import context, icurry, utility
from .....common import T_SETGRD, T_CONSTR, T_VAR, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from ..... import show
import collections
import numbers
import operator

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
          'cannot %s %r (arity=%d), with %d arg%s' % (
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
      info.typecheck(info, *successors)
    self.successors = successors
    return self

  def __copy__(self):
    return self.copy()

  def copy(self):
    from .copy import copynode
    return copynode(self)

  def __deepcopy__(self, memo=None):
    from .copy import copygraph
    return copygraph(self, memo=memo)

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

  def rewrite(self, info, *args, **kwds):
    Node(info, *args, target=self, **kwds)

  def __str__(self):
    return show.show(self)

  def __repr__(self):
    return show.show(self, style='repr')

context.Node.register(Node)

