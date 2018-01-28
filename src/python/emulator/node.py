import collections

InfoTable = collections.namedtuple('InfoTable', ['name', 'arity', 'step', 'show'])

class TypeInfo(object):
  '''Compile-time type info.'''
  def __init__(self, info):
    self.info = info

  def _check_call(self, args):
    if len(args) != self.info.arity:
      raise TypeError(
          'cannot construct "%s" (arity=%d), with %d args'
              % (self.info.name, self.info.arity, len(args))
        )

  def __call__(self, *args):
    '''Constructs an object of this type.'''
    self._check_call(args)
    return Node(self.info, args)

class Node(object):
  '''An expression node.'''
  def __new__(cls, info, successors=[]):
    self = object.__new__(cls)
    self.replace(info, successors)
    return self

  def replace(self, info, successors=[]):
    self.info = info
    self.successors = list(successors)

  def __eq__(self, rhs):
    return self.info == rhs.info and self.successors == rhs.successors

  def __ne__(self, rhs):
    return not (self == rhs)

  def __str__(self):
    return self.info.show(self)

  def __repr__(self):
    return '<%s %s>' % (self.info.name, self.successors)

