from ..visitation import dispatch
import textwrap

T_FAIL   = -4
T_FWD    = -3
T_CHOICE = -2
T_FUNC   = -1
T_CTOR   =  0

class E_SYMBOL(BaseException):
  '''
  Indicates a symbol requiring exceptional handing (i.e., FAIL or CHOICE) was
  encountered in a needed position.  
  '''
  pass

class InfoTable(object):
  '''The runtime data stored in the ``info`` slot of every node.'''
  __slots__ = ['name', 'arity', 'tag', 'step', 'show']
  def __init__(self, name, arity, tag, step, show):
    self.name = name
    self.arity = arity
    self.tag = tag
    self.step = step
    self.show = show

  def __repr__(self):
    return ''.join([
        'InfoTable('
      , ', '.join('%s=%s' % (
            slot, getattr(self, slot)) for slot in self.__slots__
          )
      , ')'
      ])

class TypeInfo(object):
  '''Compile-time type info.'''
  def __init__(self, ident, info):
    self.ident = ident
    self.info = info

  def _check_call(self, *args):
    if len(args) != self.info.arity:
      raise TypeError(
          'cannot construct "%s" (arity=%d), with %d args'
              % (self.info.name, self.info.arity, len(args))
        )

  def __call__(self, *args):
    '''Constructs an object of this type.'''
    self._check_call(*args)
    return Node(self.info, *args)

  def __str__(self):
    return 'TypeInfo for %s' % self.ident

 
class Node(object):
  '''An expression node.'''
  def __new__(cls, info, *args):
    self = object.__new__(cls)
    self.rewrite(info, *args)
    return self

  def rewrite(self, info, *args):
    self.info = info
    self.successors = list(args)

  def __getitem__(self, i):
    '''Get a successor, skipping over FWD nodes.'''
    assert self.info.tag != T_FWD
    x = self.successors[i]
    while hasattr(x, 'info') and x.info.tag == T_FWD:
      x = x[0] 
    return x

  def __eq__(self, rhs):
    return self.info == rhs.info and self.successors == rhs.successors

  def __ne__(self, rhs):
    return not (self == rhs)

  def __str__(self):
    return self.info.show(self)

  def __repr__(self):
    return '<%s %s>' % (self.info.name, self.successors)

  # An alias for ``Node.write``.  This gives a consistent syntax for node
  # creation and rewriting.  For example, ``node(*args)`` creates a node and
  # ``lhs.node(*args)`` rewrites ``lhs``.
  node = rewrite

# An alias for node creation.
node = Node

