from . import runtime
from ..utility import visitation

class Show(object):
  '''Implements the built-in show function.'''
  def __new__(cls, interp, format=None):
    return format if callable(format) else object.__new__(cls, interp, format)

  def __init__(self, interp, format=None):
    self.format = getattr(format, 'format', None) # i.e., str.format.
    # Note: Show objects can be created before interp.prelude exists (i.e.,
    # while loading the prelude itself).  In that case, omit handling for
    # forward nodes.
    try:
      self.ni_Fwd = interp.prelude._Fwd
    except AttributeError:
      self.ni_Fwd = None

  def __call__(self, node):
    '''Applies type-specific formatting after recursing to subexpressions.'''
    assert isinstance(node, runtime.Node)
    # FIXME: rather than put ? in this list, it would be better to check
    # whether the operation is infix and compare its precedence to the outer
    # expression.
    noparen = (node.info.name and node.info.name[0] in '([{<?') or \
        node.info is self.ni_Fwd
    subexprs = self.generate(node, self._recurse_, noparen)
    if self.format is None:
      return ' '.join(subexprs)
    else:
      subexprs = list(subexprs)
      return self.format(*subexprs)

  @staticmethod
  def generate(node, xform, noparen):
    yield node.info.name
    for expr in node.successors:
      yield xform(expr, noparen)

  @visitation.dispatch.on('expr')
  def _recurse_(self, expr, noparen):
    '''Recursively application.  Parenthesizes subexpressions.'''
    return str(expr)

  @_recurse_.when(runtime.Node)
  def _recurse_(self, node, noparen):
    x = node.info.show(node)
    if noparen or not x or x[0] in '([{<' or ' ' not in x or node.info is self.ni_Fwd:
      return x
    else:
      return '(%s)' % x

