from .iobject import IObject
from .iexpression import IVar, IVarAccess
from ...utility.formatting import indent, wrapblock
from ...utility import translateKwds
import abc, six

__all__ = [
    'IAssign', 'IBlock', 'ICase', 'ICaseCons', 'ICaseLit', 'IConsBranch'
  , 'IExempt', 'IFreeDecl', 'ILitBranch', 'INodeAssign', 'IReturn'
  , 'IStatement', 'IVarAssign', 'IVarDecl'
  ]

class IBlock(IObject):
  def __init__(self, vardecls, assigns, stmt, **kwds):
    self.vardecls = tuple(vardecls)
    self.assigns = tuple(assigns)
    self.stmt = stmt
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.vardecls + self.assigns + (self.stms,)
  def __str__(self):
    lines = map(str, self.vardecls)
    lines += map(str, self.assigns)
    lines.append(str(self.stmt))
    return '\n'.join(lines)
  def __repr__(self):
    return 'IBlock(vardecls=%r, assigns=%r, stmt=%r)' % (
        self.vardecls, self.assigns, self.stmt
      )

class IFreeDecl(IObject):
  def __init__(self, vid, **kwds):
    self.vid = vid
    IObject.__init__(self, **kwds)
  @property
  def lhs(self):
    return IVar(self.vid)
  def __str__(self):
    return 'free %s' % IVar(self.vid)
  def __repr__(self):
    return 'IFreeDecl(vid=%r)' % self.vid

class IVarDecl(six.with_metaclass(abc.ABCMeta, IObject)):
  def __init__(self, vid, **kwds):
    self.vid = vid
    IObject.__init__(self, **kwds)
  @property
  def lhs(self):
    return IVar(self.vid)
  def __str__(self):
    return 'var %s' % IVar(self.vid)
  def __repr__(self):
    return 'IVarDecl(vid=%r)' % self.vid
IVarDecl.register(IFreeDecl)

class IVarAssign(IObject):
  def __init__(self, vid, expr, **kwds):
    self.vid = vid
    self.expr = expr
    IObject.__init__(self, **kwds)
  _fields_ = 'vid', 'expr'
  @property
  def lhs(self):
    return IVar(self.vid)
  @property
  def rhs(self):
    return self.expr
  @property
  def children(self):
    return self.expr,
  def __str__(self):
    return '%s <- %s' % (IVar(self.vid), self.expr)
  def __repr__(self):
    return 'IVarAssign(vid=%r, expr=%r)' % (self.vid, self.expr)

class INodeAssign(IObject):
  def __init__(self, vid, path, expr, **kwds):
    self.vid = vid
    self.path = path
    self.expr = expr
    IObject.__init__(self, **kwds)
  _fields_ = 'vid', 'path', 'expr'
  @property
  def lhs(self):
    return IVarAccess(self.vid, self.path)
  @property
  def rhs(self):
    return self.expr
  @property
  def children(self):
    return self.expr,
  def __str__(self):
    return '%s <- %s' % (
        IVarAccess(self.vid, self.path), self.expr
      )
  def __repr__(self):
    return 'INodeAssign(vid=%r, path=%r, expr=%r)' % (
        self.vid, self.path, self.expr
      )

class IAssign(six.with_metaclass(abc.ABCMeta, IObject)):
  pass
IAssign.register(IVarAssign)
IAssign.register(INodeAssign)

class IExempt(IObject):
  def __str__(self):
    return 'exempt'
  def __repr__(self):
    return 'IExempt()'

class IReturn(IObject):
  def __init__(self, expr, **kwds):
    self.expr = expr
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.expr,
  def __str__(self):
    return 'return %s' % self.expr
  def __repr__(self):
    return 'IReturn(expr=%r)' % self.expr

class ICase(IObject):
  def __init__(self, vid, branches, **kwds):
    self.vid = vid
    self.branches = branches
    IObject.__init__(self, **kwds)
  _fields_ = 'vid', 'branches'
  @property
  def var(self):
    return IVar(self.vid)
  @property
  def children(self):
    return self.branches
  def __str__(self):
    return 'case %s of\n%s' % (
        self.var
      , indent(self.branches)
      )
  def __repr__(self):
    return '%s(vid=%r, branches=%r)' % (
        type(self).__name__, self.vid, self.branches
      )

class ICaseCons(ICase): pass
class ICaseLit(ICase): pass

class IConsBranch(IObject):
  @translateKwds({'name': 'symbolname'})
  def __init__(self, symbolname, arity, block, **kwds):
    self.symbolname = symbolname
    self.arity = arity
    self.block = block
    IObject.__init__(self, **kwds)
  _fields_ = 'symbolname', 'arity', 'block'
  @property
  def children(self):
    return self.block,
  def __str__(self):
    return '%s %s->%s' % (self.symbolname, ''.join('_ ' * self.arity), wrapblock(self.block))
  def __repr__(self):
    return 'IConsBranch(symbolname=%r, arity=%r, block=%r)' % (
        self.symbolname, self.arity, self.block
      )

class ILitBranch(IObject):
  def __init__(self, lit, block, **kwds):
    self.lit = lit
    self.block = block
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.lit, self.block
  def __str__(self):
    return '%s ->%s' % (self.lit, wrapblock(self.block))
  def __repr__(self):
    return 'ILitBranch(lit=%r, block=%r)' % (self.lit, self.block)


class IStatement(six.with_metaclass(abc.ABCMeta, IObject)):
  pass

IStatement.register(IAssign)
IStatement.register(IBlock)
IStatement.register(ICaseCons)
IStatement.register(ICaseLit)
IStatement.register(IExempt)
IStatement.register(IReturn)
IStatement.register(IVarDecl)
