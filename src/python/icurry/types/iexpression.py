from .iobject import IObject
from ...utility import translateKwds
import abc, copy

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

class IReference(IObject, metaclass=abc.ABCMeta):
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
  def __deepcopy__(self, memo):
    return _deepcopy_expression(self, memo)
  def __str__(self):
    string = ', '.join(
        [repr(self.symbolname)] \
      + [str(x) for x in self.exprs]
      )
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
  def __deepcopy__(self, memo):
    return _deepcopy_expression(self, memo)
  def __str__(self):
    return '%s ? %s' % (self.lhs, self.rhs)
  def __repr__(self):
    return 'IOr(lhs=%r, rhs=%r)' % (self.lhs, self.rhs)

class IExpression(IObject, metaclass=abc.ABCMeta):
  pass


def _deepcopy_expression(root, memo):
  '''
  The deep copy of the call or choice ``root`` under ``memo``, the memo of
  copy.deepcopy, which ICall.__deepcopy__ and IOr.__deepcopy__ call.  The
  copy walks the nested calls and choices on a stack of its own: through
  the generic protocol of copy.deepcopy the nest of cons calls of a literal
  list cost six frames per element, and a list of about 2700 elements ran
  out of frames under maxrecursion in the inliner (issue #125).  Every
  other attribute of a node, and every part that is not a call or a
  choice, is copied by copy.deepcopy under the same memo, so the copy is
  the one copy.deepcopy made: a part shared within the expression is
  copied once, and the metadata of a node is copied with it.
  '''
  keep = memo.setdefault(id(memo), [])
  stack = []
  def fresh(node):
    # A new object of the class of ``node``, on record in the memo before
    # its parts are copied, as copy.deepcopy records a copy.
    cls = type(node)
    new = cls.__new__(cls)
    memo[id(node)] = new
    keep.append(node)
    return new
  def part(value):
    if isinstance(value, (ICall, IOr)):
      found = memo.get(id(value))
      if found is not None:
        return found
      new = fresh(value)
      stack.append((value, new))
      return new
    return copy.deepcopy(value, memo)
  result = fresh(root)
  stack.append((root, result))
  while stack:
    node, new = stack.pop()
    for key, value in node.__dict__.items():
      if key == 'exprs' and isinstance(node, ICall):
        new.__dict__[key] = [part(e) for e in value]
      elif key in ('lhs', 'rhs') and isinstance(node, IOr):
        new.__dict__[key] = part(value)
      else:
        new.__dict__[key] = copy.deepcopy(value, memo)
  return result

IExpression.register(IVar)
IExpression.register(IVarAccess)
IExpression.register(ILit)
IExpression.register(ICall)
IExpression.register(IOr)

IExpr = IExpression

