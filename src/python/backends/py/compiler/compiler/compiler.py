from .function import compileF
from .....icurry import analysis
from ..... import icurry, objects
from .. import ir, render, statics
from .....utility import encoding, filesys, visitation
import collections, pprint, sys, textwrap

__all__ = ['FunctionCompiler']

class FunctionCompiler(object):
  '''
  Compiles an ICurry function description into a step function implemented as a
  Python function.

  Assembles list-formatted Python code (see ``render``).

  The compiler may generate local variables.  To avoid name clashes, the
  following names are reserved:

    System functions:
        The runtime system is passed via a variable named "rts".  All methods
        of the runtime system are accessed through this object.

    ICurry Variables:
        ``_$i``, where $i is the numeric variable ID (``vid`` in ICurry).  The
        redex root, denoted _0, is passed as an argument to the function.

    Static data:
        Static variables begin with two lowercase characters followed
        by an underscore.  E.g., ty_List for the list type, or ni_Nil for the empty
        list constructor.  See statics.py for details.
  '''
  def __init__(self, interp, ifun, closure, entry, extern=None):
    assert isinstance(ifun, icurry.IFunction)
    self.interp = interp
    self.ifun = ifun
    self.closure = closure
    self.entry = entry
    self.extern = extern
    #
    self.lines = [('def %s(rts, _0):' % self.entry, ifun.fullname)]
    self.varinfo = None

  def __str__(self):
    code = render.render(self.lines, istart=1)
    maxlen = max(map(len, self.closure.data.keys()) or [0])
    fmt = '  %%-%ds -> %%s' % min(maxlen, 25)
    lines = []
    lines += ['Closure:'
           ,  '--------']
    # lines += [fmt % item for item in sorted(self.closure.data.items())]
    cpred = lambda cname: cname in code
    lines += render.render(self.closure, cpred=cpred).split('\n')
    lines += ['', 'Code:'
                , '-----']
    lines += code.split('\n')
    return '\n'.join(lines)

  def compile(self):
    # ICurry data can be deeply nested.  Adjusting the recursion limit up from
    # its default of 1000 is necessary, e.g., to process strings longer than
    # 999 characters.
    limit = sys.getrecursionlimit()
    self.varinfo = analysis.varinfo(self.ifun.body)
    try:
      sys.setrecursionlimit(1<<30)
      compileF(self, self.ifun)
    finally:
      sys.setrecursionlimit(limit)
      self.varinfo = None

  def intern(self, obj):
    '''Internalize an object into the static section.'''
    if isinstance(obj, str):
      obj = self.interp.symbol(obj)
    return self.closure.intern(obj)

