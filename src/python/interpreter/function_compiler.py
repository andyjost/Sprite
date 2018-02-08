from .. import icurry
from ..visitation import dispatch
from . import analysis
from . import runtime
import collections
import itertools
import logging
import re

logger = logging.getLogger(__name__)

def compile_function(interpreter, ifun):
  '''Compiles an ICurry function into a Python step function.'''
  assert isinstance(ifun, icurry.IFunction)
  if ifun.metadata:
    return compile_primitive_builtin(interpreter, ifun)
  compiler = FunctionCompiler(interpreter)
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

def compile_primitive_builtin(interpreter, ifun):
  '''
  Compiles code for built-in functions on primitive data

  For these, the IFunction.metadata is bound to a function that implements the
  function.
  '''
  func = ifun.metadata
  hnf = interpreter.hnf
  if interpreter.flags.get('debug', True):
    def step(lhs):
      hnfs = (hnf(lhs, [i]) for i in xrange(len(lhs.successors)))
      tys, args = zip(*[(s.info, s[0]) for s in hnfs])
      assert all(isinstance(arg, icurry.BuiltinVariant) for arg in args)
      tys = set(tys)
      ti_result = tys.pop()
      assert not tys
      result = func(*args)
      lhs.rewrite(ti_result, result)
  else:
    def step(lhs):
      args = (hnf(lhs, [i])[0] for i in xrange(len(lhs.successors)))
      lhs.rewrite(lhs[0].info, func(*args))
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
  def __new__(self, interpreter):
    self = object.__new__(self)
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
    exec render(self.program) in self.closure.context, local
    return local['step']

  def typeinfo(self, iname):
    '''Get the TypeInfo object for a program symbol.'''
    return self.interpreter[iname]

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
    # Tolerate empty functions.
    body = self.program[-1]
    if not body:
      body += ['pass']

  # Compile top-level ICurry objects.
  @dispatch.on('iobj')
  def _compile(self, iobj):
    raise RuntimeError('unhandled ICurry type: %s' % type(iobj))

  @_compile.when(collections.Sequence)
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
    raise RuntimeError('unhandled VarScope: %s' % type(varscope))

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
    raise RuntimeError('unhandled VarScope: %s' % type(varscope))

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
  def expression(self, expression):
    raise RuntimeError('unhandled Expression: %s' % type(expression))

  @expression.when(collections.Sequence)
  def expression(self, seq):
    return map(self.expression, seq)

  @expression.when(icurry.Exempt)
  def expression(self, exempt):
    raise RuntimeError('Exempt not handled')

  @expression.when(icurry.Reference)
  def expression(self, ref):
    return 'node(%s, _%s)' % (self.closure['Prelude.Fwd'], ref.vid)

  @expression.when(icurry.Applic)
  def expression(self, applic):
    return 'node(%s%s)' % (
        self.closure[applic.ident]
      , ''.join(', '+e for e in self.expression(applic.args))
      )

  @expression.when(icurry.PartApplic)
  def expression(self, partapplic):
    raise RuntimeError('PartApplilc not handled')

  @expression.when(icurry.IOr)
  def expression(self, ior):
    choice = self.closure['Prelude.Choice']
    return 'node(%s, %s, %s)' % (
        choice, self.expression(ior.lhs), self.expression(ior.rhs)
      )

  @expression.when(icurry.BuiltinVariant)
  def expression(self, value):
    return repr(value)

  # Statement.
  @dispatch.on('statement')
  def statement(self, statement):
    raise RuntimeError('unhandled Statement: %s' % type(statement))

  @statement.when(collections.Sequence)
  def statement(self, seq):
    for lines in map(self.statement, seq):
      for line in lines:
        yield line

  @statement.when(icurry.IExternal)
  def statement(self, iexternal):
    raise RuntimeError('IExternal not handled')

  @statement.when(icurry.Comment)
  def statement(self, comment):
    raise RuntimeError('Comment not handled')

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
    if analysis.is_value(return_.expr):
      yield 'return True'
    else:
      yield 'return False'

  @statement.when(icurry.ATable)
  def statement(self, atable):
    self.closure['hnf'] = self.interpreter.hnf
    # How would one pull-tab a detached expression?  It cannot be done.  So the
    # selector must be a variable.
    assert hasattr(atable.expr, 'vid')
    yield 'selector = hnf(lhs, p_%s).info.tag' % atable.expr.vid
    cf = 'if'
    for iname,stmt in atable.cases.iteritems():
      yield '%s selector == %s:' % (cf, self.typeinfo(iname).info.tag)
      yield list(self.statement(stmt))
      cf = 'elif'
    if atable.isflex:
      yield 'else:'
      yield [
          'lhs.node(%s)' % self.closure['Prelude.Failure']
        , 'return'
        ]

  @statement.when(icurry.BTable)
  def statement(self, btable):
    yield ''
    # builtins
    # raise RuntimeError('BTable not handled')


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

  def encode(self, iname):
    # First, try just the basename (with illegal characters removed).
    a = str(re.sub(self.PATTERN, '', iname.basename))
    k = 'ti_' + a
    if k in self.context:
      # If it conflicts, try prepending the module name.
      k = 'ti_%s_%s' % (iname.module, a)
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
    symbol = self.interpreter[iname].info
    for k,v in self.context.iteritems():
      if v is symbol:
        return k
    else:
      k = self.encode(iname)
      self.context[k] = symbol
      return k

  def __setitem__(self, key, obj):
    '''Add a non-symbol, such as a system function, to the closure.'''
    if key.startswith('ti_') or key.startswith('_') or '.' in key:
      raise RuntimeError('Illegal system name in step function closure')
    if self.context.get(key, obj) is not obj:
      raise RuntimeError('Name conflict in step function closure')
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

@indent.when(collections.Sequence)
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

