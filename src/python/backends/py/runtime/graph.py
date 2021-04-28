from __future__ import absolute_import
from .... import icurry
from ....utility import visitation
import collections
import numbers
import operator

__all__ = [
    'T_FAIL', 'T_BIND', 'T_FREE', 'T_FWD', 'T_CHOICE', 'T_FUNC', 'T_CTOR'
  , 'InfoTable', 'NodeInfo', 'Node'
  ]

T_FAIL   = -6
T_BIND   = -5
T_FREE   = -4
T_FWD    = -3
T_CHOICE = -2
T_FUNC   = -1
T_CTOR   =  0 # for each type, ctors are numbered starting at zero.

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
    # the first time it is accessed.  LazyFunction is a tuple that omits lengthy
    # details from the representation.
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
      , ', '.join('%s=%r' % (
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
  ``name``
      The fully-qualified Curry identifier for this kind of node.
  ``info``
      An instance of ``InfoTable``.
  '''
  def __init__(self, icurry, info):
    self.icurry = icurry
    self.info = info

  @property
  def name(self):
    return self.icurry.name

  # TODO: add getsource to get the Curry source.  It will require an
  # enhancement to CMC and maybe FlatCurry to generate source range
  # annotations.

  @property
  def fullname(self):
    return '%s.%s' % (self.icurry.modulename, self.name)

  def getimpl(self):
    '''Returns the implementation code of the step function, if available.'''
    step = self.info.step
    try:
      return getattr(step, 'source')
    except AttributeError:
      raise ValueError(
          'no implementation code available for "%s"' % self.fullname
        )

  def __str__(self):
    return self.name

  def __repr__(self):
    if self.info.tag >= T_CTOR:
      return "<curry constructor '%s'>" % self.name
    if self.info.tag == T_FUNC:
      return "<curry function '%s'>" % self.name
    if self.info.tag == T_CHOICE:
      return "<curry choice>"
    if self.info.tag == T_FWD:
      return "<curry forward node>"
    if self.info.tag == T_FAIL:
      return "<curry failure>"
    if self.info.tag == T_FREE:
      return "<curry free variable>"
    if self.info.tag == T_BIND:
      return "<curry constraint>"
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
    # This assert is only valid when direct_var_binding is False.
    # assert target is None or \
    #        target.info.tag == T_FUNC or \
    #        (target.info.tag == T_FREE == info.tag)
    self = object.__new__(cls) if target is None else target
    self.info = info
    successors = list(args)
    # Run-time typecheck (debug only).
    if info.typecheck is not None:
      info.typecheck(*successors)
    self.successors = successors
    return self

  def __copy__(self):
    return self.copy()

  def copy(self):
    return Node(self.info, *self)

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
      assert isinstance(node, icurry.ILiteral)
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
    # Use __getitem__ to compress paths.  Forward nodes do not influence
    # structural equality.
    if self.info != rhs.info:
      return False
    if len(self.successors) != len(rhs.successors):
      return False
    return all(self[i] == rhs[i] for i in xrange(len(self.successors)))

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

  def rewrite(self, info, *args):
    Node(info, *args, target=self)

