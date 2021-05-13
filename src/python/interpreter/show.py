from .. import context
from ..utility import visitation

# Apply special formatting for unboxed literals; e.g., 1# is an unboxed Int
# with value 1.
@visitation.dispatch.on('arg')
def showlit(arg):
  return '%r' % arg

@showlit.when(int)
def showlit(lit):
  return '%r#' % lit

@showlit.when(float)
def showlit(lit):
  return '%r#' % lit

@showlit.when(str)
def showlit(lit):
  assert len(lit) == 1
  return '%r#' % lit

class Show(object):
  '''Implements the built-in show function.'''
  def __new__(cls, interp, format=None, showlit=showlit):
    return format if callable(format) else object.__new__(cls, interp, format)

  def __init__(self, interp, format=None, showlit=showlit):
    self.format = getattr(format, 'format', None) # i.e., str.format.
    self.showlit = showlit
    # Note: Show objects can be created before interp.prelude exists (i.e.,
    # while loading the prelude itself).  In that case, omit handling for
    # forward nodes.
    try:
      self.ni_Fwd = interp.prelude._Fwd
    except AttributeError:
      self.ni_Fwd = None

  def __call__(self, node):
    '''Applies type-specific formatting after recursing to subexpressions.'''
    assert isinstance(node, context.Node)
    # FIXME: rather than put ? in this list, it would be better to check
    # whether the operation is infix and compare its precedence to the outer
    # expression.
    noparen = (node.info.name and node.info.name[0] in '([{<?') or \
        node.info is self.ni_Fwd
    subexprs = self.generate(node, self._recurse_, noparen)
    if self.format is None or len(node) < node.info.arity:
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
    '''Recursive application.  Parenthesizes subexpressions.'''
    return self.showlit(expr)

  @_recurse_.when(context.Node)
  def _recurse_(self, node, noparen):
    x = node.info.show(node)
    if noparen or not x or x[0] in '([{<' or ' ' not in x or node.info is self.ni_Fwd:
      return x
    else:
      return '(%s)' % x

