from ....icurry import analysis
from . import closure
from .... import icurry
from . import render
from ..runtime import graph
from ..runtime import prelude_impl
from ....utility import encoding, visitation, formatDocstring
from ....utility import filesys
import collections
import logging
import pprint
import re
import sys
import textwrap

logger = logging.getLogger(__name__)

class ExternallyDefined(Exception):
  '''
  Raised to indicate that a function is externally defined.  Provides the
  replacement.
  '''
  def __init__(self, ifun):
    self.ifun = ifun

@formatDocstring(__package__[:__package__.find('.')])
def compile_function(interp, ifun, extern=None):
  '''
  Compiles an ICurry function into a Python step function.

  Parameters:
  -----------
  ``interp``
      The interpreter that owns this function.
  ``ifunc``
      ICurry for the function to compile.
  ``extern``
      An instance of ``{0}.icurry.IModule`` used to resolve external
      declarations.
  '''
  while True:
    try:
      assert isinstance(ifun, icurry.IFunction)
      assert 2 >= sum(1
          for k in ['py.boxedfunc', 'py.rawfunc', 'py.unboxedfunc']
          if k in ifun.metadata
        )
      if 'py.unboxedfunc' in ifun.metadata:
        return compile_py_unboxedfunc(interp, ifun.metadata)
      elif 'py.boxedfunc' in ifun.metadata:
        return compile_py_boxedfunc(interp, ifun.metadata)
      elif 'py.rawfunc' in ifun.metadata:
        return compile_py_rawfunc(interp, ifun.metadata)
      compiler = FunctionCompiler(interp, ifun, extern)
      compiler.compile()
    except ExternallyDefined as e:
      ifun = e.ifun
    else:
      break

  if logger.isEnabledFor(logging.DEBUG):
    title = 'Compiling %r:' % ifun.fullname
    logger.debug('')
    logger.debug(title)
    logger.debug('=' * len(title))
    logger.debug('    ICurry:')
    logger.debug('    -------')
    [logger.debug('    ' + line if line else '')
        for line in str(ifun).split('\n')
      ]
    logger.debug('')
    [logger.debug('    ' + line if line else '')
        for line in str(compiler).split('\n')
      ]
  return compiler.get()

def compile_py_boxedfunc(interp, metadata):
  '''
  Compiles code for a built-in function.  See README.md.  Corresponds to the
  "py.boxedfunc" metadata.

  The Python implementation function must accept the arguments in head-normal
  form, but without any other preprocessing (e.g., unboxing).  It returns a
  sequence of arguments accepted by ``runtime.Node.__new__``.
  '''
  boxedfunc = metadata['py.boxedfunc']
  def step(rts, _0):
    args = (rts.variable(_0, i).hnf() for i in xrange(len(_0.successors)))
    _0.rewrite(*boxedfunc(rts, *args))
  return step

def compile_py_rawfunc(interp, metadata):
  '''
  Compiles code for a raw built-in function.  See README.md.  Corresponds to
  the "py.rawfunc" metadata.

  Like compile_py_boxedfunc but does not head-normalize the arguments.  The
  left-hand-side expression is simply passed to the implementation function.
  '''
  rawfunc = metadata['py.rawfunc']
  def step(rts, _0):
    graph.Node(*rawfunc(rts, _0), target=_0.target)
  return step

def compile_py_unboxedfunc(interp, metadata):
  '''
  Compiles code for built-in functions on primitive data.  See README.md.
  Corresponds to the "py.unboxedfunc" metadata.
  '''
  unboxedfunc = metadata['py.unboxedfunc']
  def step(rts, _0):
    args = (
        rts.variable(_0, i).hnf().unboxed_value
            for i in reversed(xrange(len(_0.successors)))
      )
    return rts.expr(unboxedfunc(*args), target=_0.target)
  return step

class FunctionCompiler(object):
  '''
  Compiles an ICurry function description into a step function implemented as a
  Python function.

  Assembles list-formatted Python code (see ``render``).  Needed symbols,
  including node ``CurryNodeLabel`` and system functions, are placed in the closure
  within which the step function is compiled.

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
  def __new__(self, interp, ifun, extern=None):
    assert isinstance(ifun, icurry.IFunction)
    self = object.__new__(self)
    self.ifun = ifun
    self.name = ifun.fullname
    self.interp = interp
    self.closure = closure.Closure(interp)
    self.closure['Node'] = graph.Node
    self.extern = extern
    self.program = ['def step(rts, _0):']
    self.varinfo = None
    return self

  def get(self):
    '''Returns the compiled step function.'''
    local = {}
    source = render.render(self.program)
    if self.interp.flags['debug']:
      # If debugging, write a source file so that PDB can step into this
      # function.
      srcdir = filesys.getDebugSourceDir()
      name = encoding.symbolToFilename(self.name)
      srcfile = filesys.makeNewfile(srcdir, name)
      with open(srcfile, 'w') as out:
        out.write(source)
        out.write('\n\n\n')
        comment = (
            'This file was created by Sprite because %s was compiled in debug '
            'mode.  It exists to help PDB show the compiled code.'
          ) % self.name
        out.write('\n'.join('# ' + line for line in textwrap.wrap(comment)))
        out.write('\n\n# Globals:\n# --------\n')
        closure = pprint.pformat(self.closure.context, indent=2)
        out.write('\n'.join('# ' + line for line in closure.split('\n')))
        out.write('\n\n# ICurry:\n# -------\n')
        out.write('\n'.join('# ' + line for line in str(self.ifun).split('\n')))
      co = compile(source, srcfile, 'exec')
      exec co in self.closure.context, local
    else:
      exec source in self.closure.context, local
    step = local['step']
    step.source = source
    return step

  def label(self, iname):
    '''Get the CurryNodeLabel object for a program symbol.'''
    return self.interp.symbol(iname)

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

  def compile(self):
    # ICurry data can be deeply nested.  Adjusting the recursion limit up from
    # its default of 1000 is necessary, e.g., to process strings longer than
    # 999 characters.
    limit = sys.getrecursionlimit()
    self.varinfo = analysis.varinfo(self.ifun.body)
    try:
      sys.setrecursionlimit(1<<30)
      self._compile(self.ifun.body)
    finally:
      sys.setrecursionlimit(limit)
      self.varinfo = None

  # Compile top-level ICurry objects.  Appends to the program, which is
  # represented as a nested list of strings.  Each string is a line of the
  # program, and each nesting is an indentation level.
  @visitation.dispatch.on('iobj')
  def _compile(self, iobj):
    assert False

  @_compile.when(collections.Sequence, no=str)
  def _compile(self, seq):
    map(self._compile, seq)

  @_compile.when(icurry.IFunction)
  def _compile(self, ifun):
    self._compile(ifun.body)

  @_compile.when(icurry.IExternal)
  def _compile(self, iexternal):
    # As far as I can tell, the external name in ICurry is redundant, since the
    # Curry syntax for an external declaration is just something like, e.g.:
    #
    #   eqChar external
    assert self.name == iexternal.symbolname
    assert self.extern is None or self.name.startswith(self.extern.fullname)
    try:
      localname = self.name[len(self.extern.fullname)+1:]
      ifun = self.extern.functions[localname]
      raise ExternallyDefined(ifun)
    except (KeyError, AttributeError):
      msg = 'external function %r is not defined' % self.name
      logger.warn(msg)
      stmt = icurry.IReturn(icurry.IFCall('Prelude.prim_error', [msg]))
      self._compile(stmt)
    else:
      self._compile(ifun)

  @_compile.when(icurry.IFuncBody)
  def _compile(self, body):
    self.program.append(list(self.statement(body.block)))

  @_compile.when(icurry.IStatement)
  def _compile(self, stmt):
    self.program.append(list(self.statement(stmt)))

  # Statements.  Returns a sequence of strings.
  @visitation.dispatch.on('statement')
  def statement(self, statement):
    assert False

  @statement.when(collections.Sequence, no=str)
  def statement(self, seq):
    for lines in map(self.statement, seq):
      for line in lines:
        yield line

  @statement.when(icurry.IVarDecl)
  def statement(self, vardecl):
    varname = self.expression(vardecl.lhs)
    yield '%s = None' % varname

  @statement.when(icurry.IFreeDecl)
  def statement(self, vardecl):
    varname = self.expression(vardecl.lhs)
    yield '%s = rts.freshvar()' % varname

  @statement.when(icurry.IVarAssign)
  def statement(self, assign):
    lhs = self.expression(assign.lhs, primary=True)
    rhs = self.expression(assign.rhs, primary=True)
    yield '%s = %s' % (lhs, rhs)

  @statement.when(icurry.INodeAssign)
  def statement(self, assign):
    lhs = self.expression(assign.lhs)
    rhs = self.expression(assign.rhs, primary=True)
    yield '%s = %s' % (lhs, rhs)

  @statement.when(icurry.IBlock)
  def statement(self, block):
    for sect in [block.vardecls, block.assigns, block.stmt]:
      for line in self.statement(sect):
        yield line

  @statement.when(icurry.IExempt)
  def statement(self, exempt):
    yield '_0.rewrite(%s)' % self.closure['Prelude._Failure']

  @statement.when(icurry.IReturn)
  def statement(self, ret):
    if isinstance(ret.expr, icurry.IReference):
      yield '_0.rewrite(%s, %s)' % (
          self.closure['Prelude._Fwd'], self.expression(ret.expr, primary=True)
        )
    else:
      yield '_0.rewrite(%s)' % self.expression(ret.expr)

  @statement.when(icurry.ICaseCons)
  def statement(self, icase):
    varident = self.expression(icase.var)
    assert icase.branches
    typedef = casetype(self.interp, icase)
    yield '%s.hnf(typedef=%s)' % (varident, self.closure[typedef])
    yield 'selector = %s.tag' % varident
    el = ''
    for branch in icase.branches[:-1]:
      rhs = self.label(branch.typename).info.tag
      yield '%sif selector == %s:' % (el, rhs)
      yield list(self.statement(branch.block))
      el = 'el'
    if el:
      yield 'else:'
      yield list(self.statement(icase.branches[-1].block))
    else:
      for line in self.statement(icase.branches[-1].block):
        yield line

  @statement.when(icurry.ICaseLit)
  def statement(self, icase):
    varident = self.expression(icase.var)
    typedef = casetype(self.interp, icase)
    self.closure['values'] = list(branch.lit.value for branch in icase.branches)
    yield '%s.hnf(typedef=%s, values=values)' % (varident, self.closure[typedef])
    yield 'selector = %s.unboxed_value' % varident
    el = ''
    for branch in icase.branches:
      rhs = repr(branch.lit.value)
      yield '%sif selector == %s:' % (el, rhs)
      yield list(self.statement(branch.block))
      el = 'el'
    last_line = '_0.rewrite(%s)' % self.closure['Prelude._Failure']
    if el:
      yield 'else:'
      yield [last_line]
    else:
      yield last_line

  # Expressions.  Returns a string.  For primary expressions, the string
  # evaluates to a value (boxed or unboxed).  For non-primary expressions, it
  # contains comma-separated arguments that may be used to construct a Node.
  @visitation.dispatch.on('expression')
  def expression(self, expression, primary=False):
    assert False

  @expression.when(icurry.IVar)
  def expression(self, ivar, primary=False):
    return '_%s' % ivar.vid

  @expression.when(icurry.IVarAccess)
  def expression(self, ivaraccess, primary=False):
    return 'rts.variable(%s, %s)' % (
        self.expression(ivaraccess.var, primary=primary)
      , ','.join(map(str, ivaraccess.path))
      )

  @expression.when(icurry.ILiteral)
  def expression(self, iliteral, primary=False):
    text = '%s, %r' % (self.closure[iliteral.fullname], iliteral.value)
    return 'Node(%s)' % text if primary else text

  @expression.when(icurry.IUnboxedLiteral)
  def expression(self, iunboxed, primary=False):
    return repr(iunboxed)

  @expression.when(icurry.ILit)
  def expression(self, ilit, primary=False):
    return self.expression(ilit.lit, primary)

  @expression.when(icurry.ICall)
  def expression(self, icall, primary=False):
    subexprs = (self.expression(x, primary=True) for x in icall.exprs)
    text = '%s%s' % (
        self.closure[icall.symbolname]
      , ''.join(', ' + e for e in subexprs)
      )
    return 'Node(%s)' % text if primary else text

  @expression.when(icurry.IPartialCall)
  def expression(self, ipcall, primary=False):
    subexprs = (self.expression(x, primary=True) for x in ipcall.exprs)
    text = '%s, %s, Node(%s%s, partial=True)' % (
        self.closure['Prelude._PartApplic']
      , self.expression(ipcall.missing)
      , self.closure[ipcall.symbolname]
      , ''.join(', ' + e for e in subexprs)
      )
    return 'Node(%s)' % text if primary else text

  @expression.when(icurry.IOr)
  def expression(self, ior, primary=False):
    text = '%s, %s, %s' % (
        self.closure['Prelude.?']
      , self.expression(ior.lhs, primary=True)
      , self.expression(ior.rhs, primary=True)
      )
    return 'Node(%s)' % text if primary else text

@visitation.dispatch.on('arg')
def casetype(interp, arg):
  assert False

@casetype.when(icurry.ICaseCons)
def casetype(interp, icase):
  return interp.symbol(icase.branches[0].typename).typedef()

@casetype.when(icurry.ICaseLit)
def casetype(interp, icase):
  return casetype(interp, icase.branches[0].lit)

@casetype.when(icurry.IInt)
def casetype(interp, _):
  return interp.type('Prelude.Int')

@casetype.when(icurry.IChar)
def casetype(interp, _):
  return interp.type('Prelude.Char')

@casetype.when(icurry.IFloat)
def casetype(interp, _):
  return interp.type('Prelude.Float')

