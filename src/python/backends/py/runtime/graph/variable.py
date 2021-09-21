from .. import fairscheme
from . import indexing, utility
from ..... import inspect
import numbers

class Variable(object):
  '''
  Represents an ordinary (non-free) Curry variable.

  This objects tracks the parent, target, path between them, and set guards
  crossed.  It is the focal point for working with expressions in generated
  code.  The objects helps with accessing and head-normalizing subexpressions,
  getting case selectors, building replacement expressions, and rewriting
  nodes.

  Attributes:
  -----------
    ``parent``
      The parent of the target expression.

    ``target``
      The Curry expression corresponding to this variable.

    ``realpath``
      The real path from ``parent`` to ``target``.

    ``guards``
      A set containing the set guards crossed on the path from ``parent`` to
      ``target``.

  Example:
  --------
    The ``Prelude.head`` function is defined as follows:

        head (a:as) = a

    Here, both 'a' and 'as' are variables.  In addition, the compiler may
    generate variables for positions in the pattern with no name in the source
    code.  This might be compiled to the following ICurry:

        var $1
        $1 <- $0[0]
        case $1 of
          Prelude.[] -> exempt
          Prelude.: _ _ ->
            var $2
            $2 <- $1[0]
            return $2

    The generated Python code might use ``Variable`` as follows:

        def step(rts, _0):
          # _0 = rts.variable(_0)    # (1)
          _1 = None
          _1 = rts.variable(_0, 0)   # (2)
          _1.hnf(typedef=ty_Nil)     # (3)
          if _1.tag == 1:            # (4)
            _0.rewrite(ni__Failure)  # (5a)
          else:
            _2 = None
            _2 = rts.variable(_1, 0)
            _0.rewrite(ni__Fwd, _2)  # (5b)

    At (1), the root variable, _0, is constructed.  This will serve as the base
    for other variables, and for rewriting.  This is in fact taken care of by
    the system before calling the step function.  At (2), the variable
    corresponding to _1 in ICurry or ':' in the source code is defined.  Step
    (3) head-normalizes the subexpression at _1.  This might introduce new
    forward nodes or set guards.  If so, ``hnf`` must update the variable
    accordingly.  The tag is inspected at (4).  At (5a,5b), the root is
    rewritten.  When considering set functions, this step might need to insert
    set guards before _2.
  '''
  def __init__(
      self, rts, parent=None, target=None, logicalpath=None, realpath=None
    , guards=None
    ):
    self.rts = rts
    self.parent = parent if parent is None or isinstance(parent, Variable) \
                         else Variable.from_root(rts, parent)
    self.target = target
    self.logicalpath = self._normpath(logicalpath)
    self.realpath = self._normpath(realpath)
    self.guards = set() if guards is None else set(guards)

  def __repr__(self):
    return '%s(logicalpath=%r, realpath=%r, guards=%r' % (
        type(self).__name__
      , self.logicalpath, self.realpath, self.guards
      )

  @staticmethod
  def _normpath(path):
    if path is not None:
      return [path] if isinstance(path, numbers.Integral) else tuple(path)

  @staticmethod
  def from_root(rts, root):
    return Variable(rts, target=root)

  @staticmethod
  def from_logicalpath(rts, parent, logicalpath):
    self = Variable(rts, parent, logicalpath=logicalpath)
    self.update()
    assert inspect.isa_curry_expr(self.target)
    assert indexing.subexpr(self.root, self.fullrealpath) is self.target
    return self

  @property
  def is_root(self):
    return self.parent is None

  @property
  def root(self):
    while not self.is_root:
      self = self.parent
    return self.target

  def update(self):
    assert self.logicalpath is not None
    self.target, self.realpath, self.guards = \
        indexing.realpath(self.parent.target, self.logicalpath)

  @property
  def tag(self):
    return inspect.tag_of(self.target)

  @property
  def is_boxed(self):
    return inspect.is_boxed(self.target)

  @property
  def unboxed_value(self):
   if self.is_boxed:
     assert inspect.isa_boxed_primitive(self.target)
     return self.target.successors[0]
   else:
     assert inspect.isa_unboxed_primitive(self.target)
     return self.target

  @property
  def freevar_id(self):
    assert inspect.isa_freevar(self.target)
    return inspect.get_freevar_id(self.target)

  @property
  def typedef(self):
    return self.target.info.typedef()

  @property
  def info(self):
    return self.target.info

  @property
  def successors(self):
    return self.target.successors

  def hnf(self, typedef=None, values=None):
    '''Head-normalizes this variable.'''
    return fairscheme.hnf(self.rts, self, typedef, values)

  def all_guards(self):
    '''Returns the set of all set IDs crossed on the path to this variable.'''
    return set.union(*[x.guards for x in self.walk()])

  @property
  def fullrealpath(self):
    '''Returns the full path from root to this variable.'''
    path = []
    for var in reversed(list(self.walk())):
      path.extend(var.realpath or [])
    return path

  def walk(self):
    '''Walk the chain of parents.'''
    while self is not None:
      yield self
      self = self.parent

  @property
  def rvalue(self):
    return self.guard(self.rts, self)

  @staticmethod
  def guard(rts, node):
    '''Places the appropriate set guards before an argument.'''
    if isinstance(node, Variable):
      return rts.guard(node.all_guards(), node.target)
    else:
      return node

  def rewrite(self, nodeinfo, *args):
    assert self.is_root
    assert inspect.isa_func(self.target)
    return self.target.rewrite(nodeinfo, *args)

  def copy_spine(self, end=None, rewrite=None):
    assert not self.is_root
    return utility.copy_spine(self.root, self.fullrealpath, end, rewrite)

