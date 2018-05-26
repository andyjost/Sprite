from .runtime import Node
from ..visitation import dispatch

class Show(object):
  '''Implements the built-in show function.'''
  def __new__(cls, ni_Fwd, format=None):
    return format if callable(format) else object.__new__(cls, ni_Fwd, format)

  def __init__(self, ni_Fwd, format=None):
    self.format = getattr(format, 'format', None) # i.e., str.format.
    self.ni_Fwd = ni_Fwd

  def __call__(self, node):
    '''Applies type-specific formatting after recursing to subexpressions.'''
    assert isinstance(node, Node)
    subexprs = self.generate(node, self._recurse_)
    if self.format is None:
      return ' '.join(subexprs)
    else:
      subexprs = list(subexprs)
      return self.format(*subexprs)

  @staticmethod
  def generate(node, xform):
    yield node.info.name
    for expr in node.successors:
      yield xform(expr)

  @dispatch.on('expr')
  def _recurse_(self, expr):
    '''Recursively application.  Parenthesizes subexpressions.'''
    return str(expr)

  @_recurse_.when(Node)
  def _recurse_(self, node):
    x = node.info.show(node)
    return '(%s)' % x if ' ' in x and node.info != self.ni_Fwd else x

