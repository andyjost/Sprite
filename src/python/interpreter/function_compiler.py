from .. import icurry
from .. import importer
from ..visitation import dispatch
# from . import analysis
from . import runtime
import collections
import itertools
import logging
import metadata
import re

logger = logging.getLogger(__name__)

def compile_function(interpreter, ifun):
  '''Compiles an ICurry function into a Python step function.'''
  assert isinstance(ifun, icurry.IFunction)
  if 'py.primfunc' in ifun.metadata:
    assert('py.func' not in ifun.metadata)
    return compile_primitive_builtin(interpreter, ifun.metadata['py.primfunc'])
  elif 'py.func' in ifun.metadata:
    return compile_builtin(interpreter, ifun.metadata['py.func'])
  compiler = FunctionCompiler(interpreter, ifun.ident)
  compiler.compile(ifun.code)

  if logger.isEnabledFor(logging.DEBUG):
    title = 'Compiling "%s":' % ifun.ident
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

def compile_primitive_builtin(interpreter, func):
  '''
  Compiles code for built-in functions on primitive data.  See metadata.py.
  '''
  hnf = interpreter.hnf
  unbox = interpreter.unbox
  tocurry = interpreter.tocurry
  def step(lhs):
    args = (unbox(hnf(lhs, [i])) for i in xrange(len(lhs.successors)))
    result = func(*args)
    ty = tocurry(type(result))
    lhs.rewrite(ty.info, result)
  return step

def compile_builtin(interpreter, func):
  '''
  Compiles code for a built-in function.  See metadata.py.

  The Python implementation function must accept the arguments in head-normal
  form, but without any other preprocessing (e.g., unboxing).  It returns a
  sequence of arguments suitable for passing to Node.rewrite.
  '''
  hnf = interpreter.hnf
  def step(lhs):
    args = (hnf(lhs, [i]) for i in xrange(len(lhs.successors)))
    lhs.rewrite(*func(interpreter, *args))
  return step

class FunctionCompiler(object):
  '''
  Compiles an ICurry function description into a step function implemented as a
  Python function.

  Assembles list-formatted Python code (see ``render``).  Needed symbols,
  including node ``TypeInfo`` and system functions, are placed in the closure
  within which the step function is compiled.

  The following naming conventions are used:

    Type Info:
        ``ti_$name``, where $name is a symbol name as defined in the source
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
  def __new__(self, interpreter, ident):
    self = object.__new__(self)
    self.ident = ident
    self.interpreter = interpreter
    self.closure = Closure(interpreter)
    # Every function should create or rewrite a node.
    self.closure['node'] = runtime.node
    body = []
    self.program = ['def step(lhs):', body]
    return self

  def get(self):
    '''Returns the compiled step function.'''
    local = {}
    source = render(self.program)
    if self.interpreter.flags['debug']:
      # If debugging, write a source file so that PDB can step into this
      # function.
      srcdir = importer.getDebugSourceDir()
      srcfile = importer.makeNewfile(srcdir, self.ident)
      with open(srcfile, 'w') as out:
        out.write(source)
      co = compile(source, srcfile, 'exec')
      exec co in self.closure.context, local
    else:
      exec source in self.closure.context, local
    return local['step']

  def typeinfo(self, iname):
    '''Get the TypeInfo object for a program symbol.'''
    return self.interpreter.symbol(iname)

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
    self._compile(iobj)

  # Compile top-level ICurry objects.
  @dispatch.on('iobj')
  def _compile(self, iobj): #pragma: no cover
    assert False

  @_compile.when(collections.Sequence, no=str)
  def _compile(self, seq):
    map(self._compile, seq)

  @_compile.when(icurry.VarScope)
  def _compile(self, varscope):
    return self.varscope(varscope)

  @_compile.when(icurry.BuiltinVariant)
  def _compile(self, builtinvariant):
    self.builtinvariant(builtinvariant)

  @_compile.when(icurry.Expression)
  def _compile(self, expression):
    self.expression(expression)

  @_compile.when(icurry.Statement)
  def _compile(self, statement):
    self.program.append(list(self.statement(statement)))

  # VarScope.
  @dispatch.on('varscope')
  def varscope(self, varscope):
    assert False #pragma: no cover

  @varscope.when(icurry.ILhs)
  def varscope(self, ilhs):
    return 'lhs[%d]' % (ilhs.index.position-1) # 1-based indexing

  @varscope.when(icurry.IVar)
  def varscope(self, ivar):
    return '_%s[%d]' % (ivar.vid, ivar.index.position-1) # 1-based indexing

  @varscope.when(icurry.IBind)
  def varscope(self, ibind):
    raise RuntimeError('IBind not handled')

  @varscope.when(icurry.IFree)
  def varscope(self, ifree):
    raise RuntimeError('IFree not handled')

  # VarPath.
  # Add a variable's path to the closure.
  @dispatch.on('varscope')
  def setvarpath(self, vid, varscope):
    assert False #pragma: no cover

  @setvarpath.when(icurry.ILhs)
  def setvarpath(self, vid, ilhs):
    self.closure['p_%s' % vid] = (ilhs.index.position-1,) # 1-based indexing

  @setvarpath.when(icurry.IVar)
  def setvarpath(self, vid, ivar):
    self.closure['p_%s' % vid] = self.closure['p_%s' % ivar.vid] + (vid,)

  @setvarpath.when(icurry.IBind)
  def setvarpath(self, vid, ibind):
    raise RuntimeError('IBind not handled')

  @setvarpath.when(icurry.IFree)
  def setvarpath(self, vid, ifree):
    raise RuntimeError('IFree not handled')

  # Expression.
  @dispatch.on('expression')
  def expression(self, expression): #pragma: no cover
    assert False

  @expression.when(collections.Sequence, no=str)
  def expression(self, seq):
    return map(self.expression, seq)

  @expression.when(icurry.Exempt)
  def expression(self, exempt):
    return 'node(%s)' % self.closure['_System.Failure']

  @expression.when(icurry.Reference)
  def expression(self, ref):
    return 'node(%s, _%s)' % (self.closure['_System.Fwd'], ref.vid)

  @expression.when(icurry.Applic)
  def expression(self, applic):
    return 'node(%s%s)' % (
        self.closure[applic.ident]
      , ''.join(', '+e for e in self.expression(applic.args))
      )

  @expression.when(icurry.PartApplic)
  def expression(self, partapplic):
    return 'node(%s, %s, %s)' % (
        self.closure['_System.PartApplic']
      , self.expression(partapplic.missing)
      , self.expression(partapplic.expr)
      )

  @expression.when(icurry.IOr)
  def expression(self, ior):
    return 'node(%s, %s, %s)' % (
        self.closure['_System.Choice']
      , self.expression(ior.lhs)
      , self.expression(ior.rhs)
      )

  @expression.when(icurry.BuiltinVariant)
  def expression(self, value):
    return repr(value)


  # Statement.
  @dispatch.on('statement')
  def statement(self, statement):
    raise RuntimeError('unhandled Statement: %s' % type(statement))

  @statement.when(collections.Sequence, no=str)
  def statement(self, seq):
    for lines in map(self.statement, seq):
      for line in lines:
        yield line

  @statement.when(icurry.IExternal)
  def statement(self, iexternal):
    raise RuntimeError('IExternal not handled')

  @statement.when(icurry.Comment)
  def statement(self, comment):
    pass

  @statement.when(icurry.Declare)
  def statement(self, declare):
    vid = declare.var.vid
    scope = declare.var.scope
    self.setvarpath(vid, scope)
    yield '_%s = %s' % (vid, self.varscope(scope))

  @statement.when(icurry.Assign)
  def statement(self, assign):
    raise RuntimeError('Assign not handled')

  @statement.when(icurry.Fill)
  def statement(self, fill):
    raise RuntimeError('Fill not handled')

  @statement.when(icurry.Return)
  def statement(self, return_):
    yield 'lhs.%s' % self.expression(return_.expr)
    yield 'return'

  @statement.when(icurry.ATable)
  def statement(self, atable):
    self.closure['hnf'] = self.interpreter.hnf
    assert hasattr(atable.expr, 'vid') # the selector is always a variable
    yield 'selector = hnf(lhs, p_%s).info.tag' % atable.expr.vid
    el = ''
    for iname,stmt in atable.switch.iteritems():
      yield '%sif selector == %s:' % (el, self.typeinfo(iname).info.tag)
      yield list(self.statement(stmt))
      el = 'el'

  @statement.when(icurry.BTable)
  def statement(self, btable):
    self.closure['hnf'] = self.interpreter.hnf
    self.closure['unbox'] = self.interpreter.unbox
    assert hasattr(btable.expr, 'vid') # the selector is always a variable
    yield 'selector = unbox(hnf(lhs, p_%s))' % btable.expr.vid
    el = ''
    for iname,stmt in btable.switch.iteritems():
      yield '%sif selector == %s:' % (el, icurry.unbox(iname))
      yield list(self.statement(stmt))
      el = 'el'

# Closure.
# ========
class Closure(object):
  '''
  The closure in which a step function is compiled.  Contains symbols looked up
  at compile time.

  The closure is automatically populated: the first time a symbol is looked up,
  it is added to the closure.

  See ``FunctionCompiler`` for naming conventions.
  '''
  def __init__(self, interpreter):
    self.interpreter = interpreter
    self.context = {}

  PATTERN = re.compile('[^0-9a-zA-Z_ ]') # Identifier characters.
  TR = {
      '&' : '_amp_'
    , '@' : '_at_'
    , '!' : '_bang_'
    , '`' : '_bt_'
    , '^' : '_car_'
    , ':' : '_col_'
    , ',' : '_com_'
    , '$' : '_dolr_'
    , '.' : '_dot_'
    , '"' : '_dq_'
    , '=' : '_eq_'
    , '\\ ': '_esc_'
    , '>' : '_gt_'
    , '{' : '_lbc_'
    , '[' : '_lbk_'
    , '(' : '_lp_'
    , '<' : '_lt_'
    , '-' : '_neg_'
    , '#' : '_hsh_'
    , '%' : '_pct_'
    , '|' : '_pipe_'
    , '+' : '_pos_'
    , '?' : '_q_'
    , '}' : '_rbc_'
    , ']' : '_rbk_'
    , ')' : '_rp_'
    , ';' : '_semi_'
    , '/' : '_sep_'
    , '\'': '_sq_'
    , '*' : '_star_'
    , '~' : '_til_'
    }

  def clean(self, s):
    # Clean up a string by encoding or removing non-alphanumeric characters.
    a = ''.join(self.TR.get(ch, ch) for ch in s)
    return str(re.sub(self.PATTERN, '', a))

  def encode(self, iname):
    # First, try just the basename.
    a = self.clean(iname.basename)
    k = 'ti_%s' % a
    if k in self.context:
      # If it conflicts, try prepending the module name.
      k = 'ti_%s_%s' % (self.clean(iname.module), a)
      if k in self.context:
        # Finally, append a number.
        k_ = k
        i = itertools.count()
        while k_ in self.context:
          k_ = '%s_%d' % (k, next(i))
        k = k_
    assert k not in self.context
    assert k.startswith('ti_')
    return k

  @dispatch.on('key')
  def __getitem__(self, key):
    '''Look up the given symbol.  Returns a variable name in the context.'''
    rv = self.context.get(key, None)
    return rv if rv is not None else self[icurry.IName(key)]

  @__getitem__.when(icurry.IName)
  def __getitem__(self, iname):
    symbol = self.interpreter.symbol(iname).info
    for k,v in self.context.iteritems():
      if v is symbol:
        return k
    else:
      k = self.encode(iname)
      self.context[k] = symbol
      return k

  def __setitem__(self, key, obj):
    '''Add a non-symbol, such as a system function, to the closure.'''
    assert not (key.startswith('ti_') or key.startswith('_') or '.' in key)
    assert not (self.context.get(key, obj) is not obj)
    self.context[key] = obj

# Rendering.
# ==========
@dispatch.on('arg')
def indent(arg, level=-1):
  '''
  Indents list-formatted Python code into a flat list of strings.  See
  ``render``.
  '''
  raise RuntimeError('Unhandled argument: %s' % type(arg))

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

