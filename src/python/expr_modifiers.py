'''
Defines modifiers used to control how Curry expressions are build.
'''
from . import icurry

__all__ = ['anchor', 'cons', 'nil', 'ref', 'unboxed']

class anchor(object):
  '''
  Creates an anchor in an expression.  This can be used to build nonlinear
  expressions.

  When no argument is supplied, the anchor name is automatically generated from
  the sequence _1, _2, ..., according to its position in a left-to-right,
  depth-first traversal.
  '''
  def __init__(self, value, name=None):
    self.value = value
    self.name = name

class ref(object):
  '''
  Creates a reference to another node in a call to ``expr``.  This can be used
  to build nonlinear expressions.

  The argument is optional when the expression contains exactly one anchor at
  the point where the reference appears.
  '''
  def __init__(self, name=None):
    self.name = name

class cons(object):
  '''Indicates a list constructor in ``expr``.'''
  def __init__(self, head, tail):
    self.head = head
    self.tail = tail

class _nil(object):
  '''Indicates a list terminator in ``expr``.'''
  pass
nil = _nil()
del _nil

class unboxed(object):
  '''Indicates that a literal passed to ``expr`` should remain unboxed.'''
  def __init__(self, value):
    if not isinstance(value, icurry.IUnboxedLiteral):
      raise TypeError('expected an unboxed literal, got %r' % value)
    self.value = value

class _setgrd(object):
  '''Indicates where to place a set guard in a call to ``expr``.'''
  def __init__(self, sid, value):
    self.sid = int(sid)
    self.value = value

class _failcls(object):
  '''Indicates where to place a failure in a call to ``expr``.'''
  pass
_fail = _failcls()
del _failcls

class _strictconstr(object):
  '''Indicates where to place a strict constraint in a call to ``expr``.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class _nonstrictconstr(object):
  '''Indicates where to place a nonstrict constraint in a call to ``expr``.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class _valuebinding(object):
  '''Indicates where to place a value binding constraint in a call to ``expr``.'''
  def __init__(self, value, pair):
    self.value = value
    self.pair = pair

class _var(object):
  '''Indicates where to place a free variable in a call to ``expr``.'''
  def __init__(self, vid):
    self.vid = int(vid)

class _fwd(object):
  '''Indicates where to place a forward node in a call to ``expr``.'''
  def __init__(self, value):
    self.value = value

class _choice(object):
  '''Indicates where to place a choice in a call to ``expr``.'''
  def __init__(self, cid, lhs, rhs):
    self.cid = int(cid)
    self.lhs = lhs
    self.rhs = rhs

