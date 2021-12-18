from . import ir, statics
from .... import config, objects
from ....utility import visitation
import collections, six, types

__all__ = ['render']

DEFAULT_HCOL              = 39
DEFAULT_INDENT            = 2
DEFAULT_WIDTH             = 80
MAX_JUSTIFY_FUNCTION_NAME = 36
MAX_JUSTIFY_NEEDED        = 8

def render(obj, **kwds):
  '''See Renderer.'''
  renderer = Renderer(**kwds)
  if isinstance(obj, ir.IR):
    return renderer.renderIR(obj)
  elif isinstance(obj, statics.Closure):
    return renderer.renderClosure(obj)
  else:
    return renderer.renderLines(obj)

class Renderer(object):
  def __init__(
      self, width=DEFAULT_WIDTH, indent=DEFAULT_INDENT, hcol=DEFAULT_HCOL
    , istart=0, cpred=None, goal=None
    ):
    '''
    Renders the Python IR as Python source code.

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
      A string of Python code.
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
    Render Python IR into the text of a Python module to define, load, and link
    the Curry module.
    '''
    return self.renderLines(self._convertIR2Lines(ir))

  def renderLines(self, pycode):
    '''
    Renders list-formatted Python code into a string containing valid Python.

    The input is possibly-nested lists of strings or string pairs.  The list
    nestings correspond to indentation levels.  Pairs are rendered as code
    followed by a comment to the right.
    '''
    return self._addPrefix(self.format(pycode))

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
    Formats one line or block of Python code, with the proper indentation.
    Long lines are split.
    '''
    assert False

  @format.when(six.string_types)
  def format(self, line, level=-1):
    prefix = ' ' * (self.indent * level)
    yield prefix + line

  @format.when(collections.Iterable, no=(str, tuple))
  def format(self, seq, level=-1):
    for line in seq:
      for rline in self.format(line, level+1):
        yield rline

  @format.when(tuple)
  def format(self, pair, level=-1):
    width = self.hcol - self.indent * level
    fmt = '%%-%ss # %%s' % width
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

  def _convertIR2Lines(self, ir):
    imodule = ir.icurry
    banner = 'Python code for Curry module %r' % imodule.fullname
    yield '# ' + '-' * len(banner)
    yield '# ' + banner
    yield '# ' + '-' * len(banner)
    yield ''
    curry = config.python_package_name()
    yield 'import %s' % curry
    yield 'from %s.icurry import \\' % curry
    yield '    IModule, IDataType, IConstructor, PUBLIC, PRIVATE'
    yield ''
    yield "if 'interp' not in globals():"
    yield '  interp = %s.getInterpreter()' % curry
    yield ''
    for line in ir.lines:
      yield line
    yield ''
    yield ''
    yield '# Interface'
    yield '# ---------'
    yield '_icurry_ = IModule.fromBOM('
    yield '    fullname=%r' % imodule.fullname
    yield '  , filename=%r' % imodule.filename
    yield '  , imports=%s'  % repr(imodule.imports)
    if not imodule.types:
      yield '  , types=[]'
    else:
      yield '  , types=['
      for prefix, itype in self._plist(six.itervalues(imodule.types), level=1):
        yield '%sIDataType(%r, [' % (prefix, itype.fullname)
        for prefix, ictor in self._plist(itype.constructors, level=2):
          yield '%s%r' % (prefix, ictor)
        yield self._close(2, '])')
      yield self._close(1, ']')
    if not imodule.functions:
      yield '  , functions=[]'
    else:
      yield '  , functions=['
      functions = imodule.functions.values()
      w1 = self._justify(
          [repr(ifun.fullname) for ifun in functions]
        , maximum=MAX_JUSTIFY_FUNCTION_NAME
        )
      w2 = self._justify(
          [repr(ifun.needed) for ifun in functions]
        , maximum=MAX_JUSTIFY_NEEDED
        )
      fmt = '%s(%-{0}r, %r, %-7r, %-{1}r, %s)'.format(w1, w2)
      for prefix, ifun in self._plist(functions, level=1):
        yield fmt % (
            prefix, ifun.fullname, ifun.arity, ifun.vis, ifun.needed
          , ifun.body.linkname
          )
      yield self._close(1, ']')
      yield self._close(0, ')')
    yield ''
    yield '_module_ = interp.import_(_icurry_)'
    yield ''
    yield ''
    yield '# Linking'
    yield '# -------'
    for line in self._convertClosure2Lines(ir.closure):
      yield line
    yield ''
    yield ''
    yield '''if __name__ == '__main__':'''
    yield   '  from %s import __main__' % config.python_package_name()
    yield   '  __main__.moduleMain(__file__, %r, goal=%r)' % (imodule.fullname, self.goal)
    yield ''
    yield ''

  def _convertClosure2Lines(self, closure):
    items = [item for item in closure.dict.items() if self.cpred(item[0])]
    width = self._justify([name for name,_ in items])
    fmt = '%-{}s = %s'.format(width)
    for name, value in sorted(items, key=_sortkey):
      if name.startswith(statics.PX_DATA):
        yield fmt % (name, value)
      elif name.startswith(statics.PX_FUNC):
        yield 'from %s import %s as %s' % (value.__module__, value.__name__, name)
      elif name.startswith(statics.PX_INFO):
        yield fmt % (name, 'interp.symbol(%r)' % value.fullname)
      elif name.startswith(statics.PX_STR):
        yield fmt % (name, '%r' % value)
      elif name.startswith(statics.PX_TYPE):
        yield fmt % (name, 'interp.type(%r)' % value.fullname)

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
