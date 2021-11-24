from .iobject import IObject
from ...utility import translateKwds
import abc, six

__all__ = [
   'IVar', 'IVarAccess', 'ILit', 'IReference', 'ICall', 'IFCall', 'ICCall'
 , 'IPartialCall', 'IFPCall', 'ICPCall', 'IOr', 'IExpression'
 ]

class IVar(IObject):
  def __init__(self, vid, **kwds):
    self.vid = vid
    IObject.__init__(self, **kwds)
  def __str__(self):
    return '$%d' % self.vid
  def __repr__(self):
    return 'IVar(vid=%r)' % self.vid

class IVarAccess(IObject):
  def __init__(self, vid, path, **kwds):
    self.vid = vid
    self.path = path
    IObject.__init__(self, **kwds)
  _fields_ = 'vid', 'path'
  @property
  def var(self):
    return IVar(self.vid)
  def __str__(self):
    return '%s[%s]' % (IVar(self.vid), '.'.join(map(str, self.path)))
  def __repr__(self):
    return 'IVarAccess(vid=%r, path=%r)' % (self.vid, self.path)

class ILit(IObject):
  def __init__(self, lit, **kwds):
    self.lit = lit
    IObject.__init__(self, **kwds)
  def __str__(self):
    return str(self.lit)
  def __repr__(self):
    return 'ILit(lit=%r)' % self.lit

class IReference(six.with_metaclass(abc.ABCMeta, IObject)):
  pass
IReference.register(IVar)
IReference.register(IVarAccess)
IReference.register(ILit)

class ICall(IObject):
  @translateKwds({'name': 'symbolname'})
  def __init__(self, symbolname, exprs=[], **kwds):
    self.symbolname = symbolname
    self.exprs = exprs
    IObject.__init__(self, **kwds)
  _fields_ = 'symbolname', 'exprs'
  @property
  def children(self):
    return self.exprs
  def __str__(self):
    string = ', '.join([repr(self.symbolname)] + map(str, self.exprs))
    return '%s(%s)' % (self.__class__.__name__, string)
  def __repr__(self):
    return '%s(symbolname=%r, exprs=%r)' % (
       type(self).__name__, self.symbolname, self.exprs
     )

class IFCall(ICall): pass
class ICCall(ICall): pass

class IPartialCall(ICall):
  @translateKwds({'name': 'symbolname'})
  def __init__(self, symbolname, missing, exprs, **kwds):
    ICall.__init__(self, symbolname, exprs, **kwds)
    self.missing = int(missing)
  _fields_ = 'symbolname', 'missing', 'exprs'
  def __repr__(self):
    return '%s(symbolname=%r, missing=%r, exprs=%r)' % (
        type(self).__name__, self.symbolname, self.missing, self.exprs
      )

class IFPCall(IPartialCall): pass
class ICPCall(IPartialCall): pass

class IOr(IObject):
  def __init__(self, lhs, rhs, **kwds):
    self.lhs = lhs
    self.rhs = rhs
    IObject.__init__(self, **kwds)
  @property
  def children(self):
    return self.lhs, self.rhs
  def __str__(self):
    return '%s ? %s' % (self.lhs, self.rhs)
  def __repr__(self):
    return 'IOr(lhs=%r, rhs=%r)' % (self.lhs, self.rhs)

class IExpression(six.with_metaclass(abc.ABCMeta, IObject)):
  pass

IExpression.register(IVar)
IExpression.register(IVarAccess)
IExpression.register(ILit)
IExpression.register(ICall)
IExpression.register(IOr)

IExpr = IExpression

