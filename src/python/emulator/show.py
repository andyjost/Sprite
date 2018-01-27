from .node import Node
from ..visitation import dispatch

class Show(object):
  '''Implements the built-in show function.'''
  def __new__(cls, format=None):
    return format if callable(format) else object.__new__(cls, format)

  def __init__(self, format=None):
    self.format = getattr(format, 'format', None) # i.e., str.format.

  @dispatch.on('arg')
  def __call__(self, arg):
    '''
    Main entry point.  Applies type-specific formatting after recursing to
    subexpressions.
    '''
    return str(arg)

  @__call__.when(Node)
  def __call__(self, node):
    subexprs = self.generate(node, self._recurse_)
    if self.format is None:
      return ' '.join(subexprs)
    else:
      subexprs = list(subexprs)
      return self.format(*subexprs)

  @staticmethod
  def generate(node, xform):
    yield node.info.name
    for arg in node.args:
      yield xform(arg)

  @dispatch.on('arg')
  def _recurse_(self, arg):
    '''Recursively application.  Parenthesizes subexpressions.'''
    return str(arg)

  @_recurse_.when(Node)
  def _recurse_(self, node):
    show = node.info.show
    if len(node.args) > 1:
      return '(%s)' % show(node)
    else:
      return show(node)

