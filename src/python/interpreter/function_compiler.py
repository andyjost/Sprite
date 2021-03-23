from .. import icurry
from . import runtime
from ..utility import encoding, visitation, formatDocstring
from ..utility import filesys
import collections
import logging
import pprint
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
      if 'py.unboxedfunc' in ifun.metadata:
        assert not any(x in ifun.metadata for x in ['py.boxedfunc', 'py.rawfunc'])
        return compile_py_unboxedfunc(interp, ifun.metadata['py.unboxedfunc'])
      elif 'py.boxedfunc' in ifun.metadata:
        assert not any(x in ifun.metadata for x in ['py.unboxedfunc', 'py.rawfunc'])
        return compile_py_boxedfunc(interp, ifun.metadata['py.boxedfunc'])
      elif 'py.rawfunc' in ifun.metadata:
        assert not any(x in ifun.metadata for x in ['py.unboxedfunc', 'py.boxedfunc'])
        return compile_py_rawfunc(interp, ifun.metadata['py.rawfunc'])
      compiler = FunctionCompiler(interp, ifun.fullname, extern)
      compiler.compile(ifun.body)
    except ExternallyDefined as e:
      ifun = e.ifun
    else:
      break

  if logger.isEnabledFor(logging.DEBUG):
    title = 'Compiling "%s":' % ifun.fullname
    logger.debug('')
    logger.debug(title)
    logger.debug('=' * len(title))
    logger.debug('    ICurry:')
    logger.debug('    -------')
    [logger.debug('        ' + line if line else '')
        for line in str(ifun).split('\n')
      ]
    logger.debug('')
    [logger.debug('    ' + line if line else '')
        for line in str(compiler).split('\n')
      ]
  return compiler.get()

def compile_py_unboxedfunc(interp, unboxedfunc):
  '''
  Compiles code for built-in functions on primitive data.  See README.md.
  Corresponds to the "py.unboxedfunc" metadata.
  '''
  hnf = interp.hnf
  expr = interp.expr
  topython = interp.topython
  def step(lhs):
    args = (topython(hnf(lhs, [i])) for i in xrange(len(lhs.successors)))
    return expr(unboxedfunc(*args), target=lhs)
  return step

def compile_py_boxedfunc(interp, boxedfunc):
  '''
  Compiles code for a built-in function.  See README.md.  Corresponds to the
  "py.boxedfunc" metadata.

  The Python implementation function must accept the arguments in head-normal
  form, but without any other preprocessing (e.g., unboxing).  It returns a
  sequence of arguments accepted by ``runtime.Node.__new__``.
  '''
  hnf = interp.hnf
  def step(lhs):
    args = (hnf(lhs, [i]) for i in xrange(len(lhs.successors)))
    runtime.Node(*boxedfunc(interp, *args), target=lhs)
  return step

def compile_py_rawfunc(interp, rawfunc):
  '''
  Compiles code for a raw built-in function.  See README.md.  Corresponds to
  the "py.rawfunc" metadata.

  Like compile_py_boxedfunc but does not head-normalize the arguments.  The
  left-hand-side expression is simply passed to the implementation function.
  '''
  def step(lhs):
    runtime.Node(*rawfunc(interp, lhs), target=lhs)
  return step

class FunctionCompiler(object):
  '''
  Compiles an ICurry function description into a step function implemented as a
  Python function.

  Assembles list-formatted Python code (see ``render``).  Needed symbols,
  including node ``NodeInfo`` and system functions, are placed in the closure
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
  def __new__(self, interp, name, extern=None):
    self = object.__new__(self)
    self.name = name
    self.interp = interp
    self.closure = Closure(interp)
    self.closure['Node'] = runtime.Node
    self.extern = extern
    # body = []
    self.program = ['def step(lhs):']
    return self

  def get(self):
    '''Returns the compiled step function.'''
    local = {}
    source = render(self.program)
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
        out.write('\n\n# Closure:\n')
        closure = pprint.pformat(self.closure.context, indent=2)
        out.write('\n'.join('# ' + line for line in closure.split('\n')))
      co = compile(source, srcfile, 'exec')
      exec co in self.closure.context, local
    else:
      exec source in self.closure.context, local
    step = local['step']
    step.source = source
    return step

  def nodeinfo(self, iname):
    '''Get the NodeInfo object for a program symbol.'''
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
    lines += indent(self.program)
    return '\n'.join(lines)

  def compile(self, iobj):
    # ICurry data can be deeply nested.  Adjusting the recursion limit up from
    # its default of 1000 is necessary, e.g., to process strings longer than
    # 999 characters.
    limit = sys.getrecursionlimit()
    try:
      sys.setrecursionlimit(1<<30)
      self._compile(iobj)
    finally:
      sys.setrecursionlimit(limit)

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
    try:
      ifun = self.extern.functions[iexternal.name]
      raise ExternallyDefined(ifun)
    except (KeyError, AttributeError):
      msg = 'external function "%s" is not defined' % iexternal.name
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
    yield '# %s' % vardecl

  @statement.when(icurry.IAssign)
  def statement(self, assign):
    lhs = self.expression(assign.lhs)
    rhs = self.expression(assign.rhs)
    yield '%s = %s' % (lhs, rhs)

  @statement.when(icurry.IBlock)
  def statement(self, block):
    for sect in [block.vardecls, block.assigns, block.stmt]:
      for line in self.statement(sect):
        yield line

  @statement.when(icurry.IExempt)
  def statement(self, exempt):
    yield 'Node(%s)' % self.closure['Prelude._Failure']

  @statement.when(icurry.IReturn)
  def statement(self, ret):
    yield 'lhs.%s' % self.expression(ret.expr)
    yield 'return'

  @statement.when(icurry.ICase)
  def statement(self, icase):
    self.closure['hnf'] = self.interp.hnf
    yield 'selector = hnf(lhs, p_%s).info.tag' % icase.vid
    el = ''
    for branch in icase.branches:
      if isinstance(branch, icurry.ILitBranch):
        rhs = repr(branch.lit.value)
      else:
        rhs = self.nodeinfo(branch.name).info.tag
      yield '%sif selector == %s:' % (el, rhs)
      yield list(self.statement(branch.block))
      el = 'el'
    yield 'else:'
    yield '  lhs.Node(%s)' % self.closure['Prelude._Failure']
    yield '  return'


  # Expressions.  Returns a string.
  @visitation.dispatch.on('expression')
  def expression(self, expression):
    import code
    code.interact(local=dict(globals(), **locals()))
    assert False

  @expression.when(collections.Sequence, no=str)
  def expression(self, seq):
    return map(self.expression, seq) ###

  @expression.when(icurry.IVar)
  def expression(self, ivar):
    return '_%s' % ivar.vid

  @expression.when(icurry.IVarAccess)
  def expression(self, ivaraccess):
    return '%s%s' % (
        self.expression(ivaraccess.var)
      , ''.join('[%s]' % i for i in ivaraccess.path)
      )

  @expression.when(icurry.ILiteral)
  def expression(self, iliteral):
    return 'Node(%s, %r)' % (self.closure[iliteral.name], iliteral.value)

  @expression.when(icurry.IUnboxedLiteral)
  def expression(self, iunboxed):
    return repr(iunboxed)

  @expression.when(icurry.ILit)
  def expression(self, ilit):
    return self.expression(ilit.lit)

  @expression.when(icurry.ICall)
  def expression(self, icall):
    return 'Node(%s%s)' % (
        self.closure[icall.name]
      , ''.join(', '+e for e in self.expression(icall.exprs)) ###
      )

  @expression.when(icurry.IPartialCall)
  def expression(self, ipcall):
    return 'Node(%s, %s%s)' % (
        self.closure['Prelude._PartApplic']
      , self.expression(ipcall.missing)
      , ''.join(', '+e for e in self.expression(ipcall.exprs))
      )

  @expression.when(icurry.IOr)
  def expression(self, ior):
    return 'Node(%s, %s, %s)' % (
        self.closure['Prelude.?']
      , self.expression(ior.lhs)
      , self.expression(ior.rhs)
      )
# Closure.
# ========
class Closure(object):
  '''
  The closure in which a step function is compiled.  Contains symbols looked up
  at compile time.

  This is a mapping from names to Python identifiers with associated objects.
  During compilation, the closure translates a name to an identifier that can
  appear in generated code as a reference to the corresponding object.  The
  mapping from identifiers to objects is exported to the runtime.

  The closure is automatically populated: the first time a symbol is looked up,
  it is added to the closure.  The value must be set once, of course, for the
  lookup to succeed at runtime.

  See ``FunctionCompiler`` for naming conventions.
  '''
  def __init__(self, interp):
    self.interp = interp
    self.context = {}

  def __getitem__(self, name):
    rv = self.context.get(name, None)
    if rv is not None:
      return rv
    else:
      symbol = self.interp.symbol(name).info
      for k,v in self.context.iteritems():
        if v is symbol:
          return k
      else:
        k = encoding.encode(name, self.context)
        self.context[k] = symbol
        return k

  def __setitem__(self, key, obj):
    '''Add a non-symbol, such as a system function, to the closure.'''
    assert not (key.startswith('ni_') or key.startswith('_') or '.' in key)
    if key not in self.context:
      self.context[key] = obj
    else: # pragma: no cover
      assert self.context[key] is obj or self.context[key] == obj

# Rendering.
# ==========
@visitation.dispatch.on('arg')
def indent(arg, level=-1):
  '''
  Indents list-formatted Python code into a flat list of strings.  See
  ``render``.
  '''
  assert False

@indent.when(str)
def indent(line, level=-1):
  yield '  ' * level + line

@indent.when(collections.Sequence, no=str)
def indent(seq, level=-1):
  for line in seq:
    for rline in indent(line, level+1):
      yield rline

def render(pycode):
  '''
  Renders list-formatted Python code into a string containing valid Python.

  The input is possibly-nested lists of strings.  The list nestings correspond
  to indentation levels.
  '''
  return '\n'.join(indent(pycode))

