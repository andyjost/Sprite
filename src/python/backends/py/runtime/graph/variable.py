from . import indexing, utility
from ..... import common, inspect

def variable(rts, parent, logicalpath=None):
  '''Creates an instance of Variable.'''
  if logicalpath is None:
    return Variable.from_root(rts, parent)
  else:
    return Variable.from_logicalpath(rts, parent, logicalpath)

class Variable(object):
  '''
  Represents an ordinary (non-free) Curry variable.

  This objects tracks a root, target, path between them, and set guards
  crossed.  It is the focal point when working with expressions in generated
  code.  These objects help with accessing and head-normalizing subexpressions,
  getting case selectors, building replacement expressions, and rewriting.

  Key Attributes:
  ---------------
    ``root``
      The function-labeled redex root.  Dominates the target expression.

    ``target``
      The Curry expression referenced by this variable.  Typically an inductive
      position of the root function.

    ``realpath``
      The real path from ``root`` to ``target``.

    ``guards``
      A set containing the set guards crossed on the path from ``root`` to
      ``target``.

    ``rvalue``
      The value to use when this variable appears in a RHS replacement
      expression.  Any guards crossed along the path from root to target are
      inserted before the target.

  Example:
  --------
    The ``Prelude.head`` function is defined as follows:

        head (a:as) = a

    Here, both 'a' and 'as' are variables.  In addition, for the purpose of
    finding redexes, the compiler generates variables for unnamed inductive
    positions, such as (:) in this example.  This might be compiled to the
    following ICurry:

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
    (3) head-normalizes the subexpression at _1.  The tag is inspected at
    (4).  At (5a,5b), the root is rewritten.  When considering set functions,
    this step might need to insert set guards before _2.
  '''
  def __init__(self, rts, root, target, realpath=None, guards=None):
    self.rts = rts
    self.root = root
    self.target = target
    self.realpath = realpath
    self.guards = set() if guards is None else guards

  @staticmethod
  def from_root(rts, parent):
    root = getattr(parent, 'root', parent)
    return Variable(rts, root, root)

  @staticmethod
  def from_logicalpath(rts, parent, logicalpath):
    root = getattr(parent, 'root', parent)
    basetarget = getattr(parent, 'target', parent)
    basepath = getattr(parent, 'realpath', None)
    baseguards = getattr(parent, 'guards', set())
    target, realpath, guards = indexing.realpath(basetarget, logicalpath)
    realpath = utility.joinpath(basepath, realpath)
    guards.update(baseguards)
    assert inspect.isa_curry_expr(target)
    assert indexing.subexpr(root, realpath) is target
    return Variable(rts, root, target, realpath, guards)

  def __repr__(self):
    return '%s(realpath=%r, guards=%r' % (
        type(self).__name__, self.realpath, self.guards
      )

  @property
  def rvalue(self):
    '''Returns the target with the appropriate set guards inserted.'''
    return self.rts.guard(self.target, self.guards)

  # Item access.
  # ------------
  def __getitem__(self, logicalpath):
    return variable(self.rts, self, logicalpath)

  def __setitem__(self, i, value):
    # Used only to construct cyclic expressions.
    assert self.successors[i] is None
    self.successors[i] = value

  # Properties.
  # -----------
  # Putting these here simplifies the generated code.  It is easier to work with
  # attributes of variables than bring in freestanding functions.

  @property
  def info(self):
    return inspect.info_of(self.target)

  @property
  def is_boxed(self):
    return inspect.is_boxed(self.target)

  @property
  def is_root(self):
    return self.root is self.target

  @property
  def successors(self):
    return self.target.successors

  @property
  def tag(self):
    return inspect.tag_of(self.target)

  @property
  def typedef(self):
    return self.target.info.typedef()

  @property
  def unboxed_value(self):
    return inspect.unboxed_value(self.target)

  # Methods.
  # --------
  # As with the properties, these methods are easier to access in generated code
  # when they are attached to variables.

  def extend(self):
    '''
    Step over a forward node or set guard at the target position.

    This might be needed, for instance, after a rewrite step that modifies the
    target.
    '''
    tag = self.tag
    if tag == common.T_SETGRD:
      sid, self.target = self.successors
      self.realpath.append(1)
      self.guards.add(sid)
    elif tag == common.T_FWD:
      self.target, = self.successors
      self.realpath.append(0)

  def hnf(self, typedef=None, values=None):
    '''Head-normalizes this variable.'''
    from .. import fairscheme
    return fairscheme.hnf(self.rts, self, typedef, values)

  def replace_target(self, replacement):
    '''Replace the target by rewriting the root.'''
    utility.copy_spine(self.root, self.realpath, end=replacement, rewrite=self.root)
    self.target = replacement

  def rewrite(self, nodeinfo, *args):
    '''Rewrite this variable.'''
    assert self.is_root
    assert inspect.isa_func(self.target)
    return self.target.rewrite(nodeinfo, *args)

