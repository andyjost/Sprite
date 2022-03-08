from ....utility import visitation
import collections, six

class SourceRenderer(object):
  HCOL        = 39
  INDENT      = 2
  WIDTH       = 80
  def __init__(self, istart=0):
    '''
    Renders the IR into source code.

    Args:
      istart:
        The starting indentation level.  This time ``indent`` gives the
        starting column for each line.

    Provided by the derived class:
      HCOL:
        The column at which to start side-by-side content.

      INDENT:
        The number of spaces to prefix for each indentation level.

      WIDTH:
        The ideal line length.

    Returns:
      A string of source code.
    '''
    self.istart = istart

  def renderLines(self, lines):
    '''
    Renders list-formatted code into a string.

    The input is possibly-nested lists of strings or string pairs.  The list
    nestings correspond to indentation levels.  Pairs are rendered as code
    followed by a comment to the right.
    '''
    return self._addPrefix(self.format(lines))

  @visitation.dispatch.on('arg')
  def format(self, arg, level=-1):
    '''
    Formats one line or block of code, with the proper indentation.  Long lines
    are split.
    '''
    assert False

  @format.when(six.string_types)
  def format(self, line, level=-1):
    prefix = ' ' * (self.INDENT * level)
    yield prefix + line

  @format.when(collections.Iterable, no=(str, tuple))
  def format(self, seq, level=-1):
    if self.BLOCK_OPEN and level >= 0:
      for line in self.format(self.BLOCK_OPEN, level):
        yield line
    for line in seq:
      for rline in self.format(line, level+1):
        yield rline
    if self.BLOCK_CLOSE and level >= 0:
      for line in self.format(self.BLOCK_CLOSE, level):
        yield line

  @format.when(tuple)
  def format(self, pair, level=-1):
    width = self.HCOL - self.INDENT * level
    fmt = '%%-%ss %s %%s' % (width, self.COMMENT_STR)
    for line in self.format(fmt % pair, level):
      yield line

  def _addPrefix(self, lines):
    prefix = ' ' * (self.INDENT * self.istart)
    if prefix:
      return '\n'.join('%s%s' % (prefix, line) for line in lines)
    else:
      return '\n'.join(lines)

  def justify(self, seq, maximum=None):
    width = max([len(x) for x in seq])
    if maximum is None:
      maximum = self.HCOL + 2 * self.INDENT + 1
    return min(width, maximum)

  def prettylist(self, seq, level=0):
    '''Formats a list as one element per line with leading commas.'''
    it = iter(seq)
    try:
      v = next(it)
    except StopIteration:
      pass
    else:
      prefill = (2 * level + 1) * self.INDENT * ' '
      fprefix = '{}%-{}s'.format(prefill, self.INDENT)
      yield fprefix % ' ', v
      commafill = fprefix % ','
      for v in it:
        yield commafill, v

class ShSourceRenderer(SourceRenderer):
  BLOCK_CLOSE = None
  BLOCK_OPEN  = None
  COMMENT_STR = '#'
  SOURCE_NAME = 'sh'

SH_RENDERER = ShSourceRenderer()

class PySourceRenderer(SourceRenderer):
  BLOCK_CLOSE = None
  BLOCK_OPEN  = None
  COMMENT_STR = '#'
  SOURCE_NAME = 'Python'

PY_RENDERER = PySourceRenderer()

class CxxSourceRenderer(SourceRenderer):
  BLOCK_CLOSE = '}'
  BLOCK_OPEN  = '{'
  COMMENT_STR = '//'
  HCOL        = 20
  SOURCE_NAME = 'C++'

CXX_RENDERER = CxxSourceRenderer()
