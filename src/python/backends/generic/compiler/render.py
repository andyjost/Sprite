from . import ir, statics
from .... import config, objects
from ....utility import visitation
import abc, collections, six, types

__all__ = ['render', 'Renderer']

DEFAULT_HCOL              = 39
DEFAULT_INDENT            = 2
DEFAULT_WIDTH             = 80

def render(obj, cls=None, **kwds):
  '''See Renderer.'''
  cls = Renderer if cls is None else cls
  renderer = cls(**kwds)
  if isinstance(obj, ir.IR):
    return renderer.renderIR(obj)
  elif isinstance(obj, statics.Closure):
    return renderer.renderClosure(obj)
  else:
    return renderer.renderLines(obj)

class Renderer(abc.ABC):
  def __init__(
      self, width=DEFAULT_WIDTH, indent=DEFAULT_INDENT, hcol=DEFAULT_HCOL
    , istart=0, cpred=None, goal=None
    ):
    '''
    Renders the IR into source code.

    Args:
      width:
        The ideal line length.

      indent:
        The number of spaces to prefix for each indentation level.

      hcol:
        The column at which to start side-by-side content.

      istart:
        The starting indentation level.  This time ``indent`` gives the
        starting column for each line.

      cpred:
        A predicate for closure keys indicating which items to include.

      goal:
        The default goal to evaluate when running in file mode.

    Returns:
      A string of source code.
    '''
    self.width = width
    self.indent = indent
    self.hcol = hcol
    self.istart = istart
    cpred = (lambda _: True) if cpred is None else cpred
    self.cpred = lambda name: \
        not name.startswith(statics.PX_SYMB) and cpred(name)
    self.goal = goal

  def renderIR(self, ir):
    '''
    Render IR into the text of a module to define, load, and link the Curry
    module.
    '''
    return self.renderLines(self._convertIR2Lines(ir))

  def renderLines(self, lines):
    '''
    Renders list-formatted code into a string.

    The input is possibly-nested lists of strings or string pairs.  The list
    nestings correspond to indentation levels.  Pairs are rendered as code
    followed by a comment to the right.
    '''
    return self._addPrefix(self.format(lines))

  def renderClosure(self, closure):
    return self._addPrefix(self._convertClosure2Lines(closure))

  def _addPrefix(self, lines):
    prefix = ' ' * (self.indent * self.istart)
    if prefix:
      return '\n'.join('%s%s' % (prefix, line) for line in lines)
    else:
      return '\n'.join(lines)

  @visitation.dispatch.on('arg')
  def format(self, arg, level=-1):
    '''
    Formats one line or block of code, with the proper indentation.  Long lines
    are split.
    '''
    assert False

  @format.when(six.string_types)
  def format(self, line, level=-1):
    prefix = ' ' * (self.indent * level)
    yield prefix + line

  @format.when(collections.Iterable, no=(str, tuple))
  def format(self, seq, level=-1):
    if self.BLOCK_OPEN and level >= 0:
      yield next(self.format(self.BLOCK_OPEN, level))
    for line in seq:
      for rline in self.format(line, level+1):
        yield rline
    if self.BLOCK_CLOSE and level >= 0:
      yield next(self.format(self.BLOCK_CLOSE, level))

  @format.when(tuple)
  def format(self, pair, level=-1):
    width = self.hcol - self.indent * level
    fmt = '%%-%ss %s %%s' % (width, self.COMMENT_STR)
    for line in self.format(fmt % pair, level):
      yield line

  def _close(self, level=0, string=']'):
    '''Prints a block-closing string at the specified intentation level.'''
    return (2 * level + 1) * self.indent * ' ' + string

  def _justify(self, seq, maximum=None):
    width = max([len(x) for x in seq])
    if maximum is None:
      maximum = self.hcol + 2 * self.indent + 1
    return min(width, maximum)

  def _plist(self, seq, level=0):
    '''Formats a list as one element per line with leading commas.'''
    it = iter(seq)
    try:
      v = next(it)
    except StopIteration:
      pass
    else:
      prefill = (2 * level + 1) * self.indent * ' '
      fprefix = '{}%-{}s'.format(prefill, self.indent)
      yield fprefix % ' ', v
      commafill = fprefix % ','
      for v in it:
        yield commafill, v

  @abc.abstractmethod
  def _convertIR2Lines(self, ir):
    pass

  @abc.abstractmethod
  def _convertClosure2Lines(self, closure):
    pass

  @staticmethod
  def _sortkey(item):
    name, value = item
    if name.startswith(statics.PX_FUNC):
      return 1, value.__module__, value.__name__
    elif name.startswith(statics.PX_INFO):
      return 2, value.fullname
    elif name.startswith(statics.PX_TYPE):
      return 3, value.fullname
    elif name.startswith(statics.PX_DATA):
      return 4, name
    else:
      return 5, name
