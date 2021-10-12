from .function import compileF
from .....icurry import analysis
from ..... import icurry, objects
from .. import misc, render, statics
from .....utility import encoding, filesys, visitation
import collections, pprint, sys, textwrap

__all__ = ['FunctionCompiler']

class FunctionCompiler(object):
  '''
  Compiles an ICurry function description into a step function implemented as a
  Python function.

  Assembles list-formatted Python code (see ``render``).

  The following naming conventions are used:

    Node Info:
        ``ni_$name``, where $name is a symbol name as defined in the source
        program with whatever modifications are required to avoid conflicts and
        make it a Python identifier.  A variant of the symbol name is used to
        improve readability while debugging.

    ICurry Variables:
        ``_$i``, where $i is the numeric variable ID (``vid`` in ICurry).

    System functions and variables:
        E.g., ``hnf`` (head-normalizing function) or ``selector`` (jump table
        selector).  No special rules; must not begin with an underscore or
        conflict with the above.
  '''
  def __init__(self, interp, ifun, extern=None, entry='entry'):
    assert isinstance(ifun, icurry.IFunction)
    self.closure = statics.Closure()
    self.entry = entry
    self.extern = extern
    self.ifun = ifun
    self.interp = interp
    self.program = ['def %s(rts, _0):' % self.entry]
    self.varinfo = None

  def __str__(self):
    maxlen = max(map(len, self.closure.context.keys()) or [0])
    fmt = '  %%-%ds -> %%s' % min(maxlen, 25)
    lines = []
    lines += ['Closure:'
           ,  '--------']
    lines += [fmt % item for item in sorted(self.closure.context.items())]
    lines += ['', 'Code:'
                , '-----']
    lines += render.indent(self.program)
    return '\n'.join(lines)

  def compile(compiler):
    # ICurry data can be deeply nested.  Adjusting the recursion limit up from
    # its default of 1000 is necessary, e.g., to process strings longer than
    # 999 characters.
    limit = sys.getrecursionlimit()
    compiler.varinfo = analysis.varinfo(compiler.ifun.body)
    try:
      sys.setrecursionlimit(1<<30)
      compileF(compiler, compiler.ifun.body)
    finally:
      sys.setrecursionlimit(limit)
      compiler.varinfo = None

  def intern(self, obj):
    '''Internalize an object into the static section.'''
    if isinstance(obj, str):
      obj = self.interp.symbol(obj)
    return self.closure.intern(obj)

  def ir(self):
    '''Get the IR.'''
    return misc.IR(self.entry, self.program, self.closure)

