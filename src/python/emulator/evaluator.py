from ..compiler.icurry import *
from .node import Node
from ..visitation import dispatch
import collections
import itertools
import logging
import re

NORMALIZE = 0
HEADNORMALIZE = 1

logger = logging.getLogger(__name__)

class Evaluator(object):
  def __new__(cls, emulator, goal):
    self = object.__new__(cls)
    self.emulator = emulator
    self.queue = [goal]
    return self

  def run(self):
    while self.queue:
      expr = self.queue.pop(0)
      is_value = False
      if not isinstance(expr, Node):
        is_value = True
      elif self.emulator.is_choice(expr):
        self.queue += expr.successors
        continue
      elif self.emulator.is_failure(expr):
        continue
      else:
        is_value = expr.info.step(expr, self.emulator, NORMALIZE)
      if is_value:
        yield expr
      else:
        self.queue.append(expr)

def ctor_step(ctor, emulator, mode):
  '''Step function for constructors.'''
  is_value = True
  for i,expr in enumerate(ctor.successors):
    if not isinstance(expr, Node):
      continue
    if emulator.is_choice(expr):
      pull_tab(ctor, [i])
      return False
    elif emulator.is_failure(expr):
      ctor.rewrite(emulator.prelude.Failure)
      return False
    else:
      is_value = is_value and expr.info.step(expr, emulator, mode)
  return is_value

def pull_tab(source, targetpath):
  '''
  Executes a pull-tab step.

  Parameters:
  -----------
    ``source``
      The ancestor, which will be overwritten.

    ``targetpath``
      A sequence of integers giving the path from ``source`` to the target
      (descendent).
  '''
  assert targetpath
  i, = targetpath # temporary
  target = source[i]
  assert target.info.name == 'Choice'
  #
  lsucc = source.successors
  lsucc[i] = target[0]
  lhs = Node(source.info, lsucc)
  #
  rsucc = source.successors
  rsucc[i] = target[1]
  rhs = Node(source.info, rsucc)
  #
  source.replace(target.info, [lhs, rhs])

def compile_function(emulator, ifun):
  assert isinstance(ifun, IFunction)
  compiler = FunctionCompiler(emulator)
  compiler.compile(ifun.code)

  if logger.isEnabledFor(logging.DEBUG):
    title = 'Compiling "%s":' % ifun.ident
    logger.debug('')
    logger.debug(title)
    logger.debug('=' * len(title))
    logger.debug('    IFunction:')
    logger.debug('    ----------')
    [logger.debug('        ' + line) for line in str(ifun).split('\n')]
    logger.debug('')
    [logger.debug('    ' + line) for line in str(compiler).split('\n')]
  return compiler.get()


# Render.
# =======
@dispatch.on('arg')
def render(arg, indent=-1):
  yield ''
  # raise RuntimeError('Unhandled argument: %s' % type(arg))

@render.when(str)
def render(line, indent=-1):
  yield '  '*indent + line

@render.when(collections.Sequence)
def render(seq, indent=-1):
  for line in seq:
    for rline in render(line, indent+1):
      yield rline

class Closure(object):
  '''
  The closure in which a step function is compiled.  Contains symbols looked up
  at compile time.
  '''
  def __init__(self, emulator):
    self.emulator = emulator
    self.context = {}

  PATTERN = re.compile('[^0-9a-zA-Z_ ]')

  def encode(self, iname):
    # First try just the basename (with illegal characters removed).
    k = str(re.sub(self.PATTERN, '', iname.basename))
    if k in self.context:
      # If it conflicts, try prepending the module name.
      k = '%s_%s' % (iname.module, k)
      if k in self.context:
        # Finally, append a number.
        kk = k
        i = itertools.count()
        while kk in self.context:
          kk = '%s_%d' % (k, next(i))
        k = kk
    assert k not in self.context
    return k

  @dispatch.on('key')
  def __getitem__(self, key):
    '''Look up the given symbol.  Returns a variable name in the context.'''
    return self[IName(key)]

  @__getitem__.when(IName)
  def __getitem__(self, iname):
    symbol = self.emulator[iname]
    for k,v in self.context.iteritems():
      if v is symbol:
        return k
    else:
      k = self.encode(iname)
      self.context[k] = symbol
      return k

class FunctionCompiler(object):
  def __new__(self, emulator):
    self = object.__new__(self)
    self.closure = Closure(emulator)
    body = []
    self.program = ['def step(lhs):', body]
    self.insertion_points = [body.append] # a stack of IPs.
    return self

  @property
  def insert(self):
    '''Inserts a line of code at the current insertion point.'''
    return self.insertion_points[-1]

  def get(self):
    '''Returns the compiled step function.'''
    local = {}
    exec '\n'.join(render(self.program)) in self.closure.context, local
    return local['step']

  def __str__(self):
    fmt = '  %%-%ds -> %%s' % max(map(len, self.closure.context.keys()) or [0])
    lines = []
    lines += ['Closure:'
           , '---------']
    lines += [fmt % item for item in self.closure.context.items()]
    lines += ['', 'Code:'
                , '-----']
    lines += render(self.program)
    return '\n'.join(lines)


  # Compile nodes.
  @dispatch.on('iobj')
  def compile(self, iobj):
    raise RuntimeError('unhandled ICurry type: %s' % type(iobj))

  @compile.when(collections.Sequence)
  def compile(self, seq):
    map(self.compile, seq)

  @compile.when(VarScope)
  def compile(self, varscope):
    return self.varscope(varscope)

  @compile.when(BuiltinVariant)
  def compile(self, builtinvariant):
    self.builtinvariant(builtinvariant)

  @compile.when(Expression)
  def compile(self, expression):
    self.expression(expression)

  @compile.when(Statement)
  def compile(self, statement):
    self.insert(self.statement(statement))

#   @compile.when(Variable)
#   def compile(self, variable):
#     pass

  # VarScope.
  @dispatch.on('varscope')
  def varscope(self, varscope):
    raise RuntimeError('unhandled VarScope: %s' % type(varscope))

  @varscope.when(ILhs)
  def varscope(self, ilhs):
    return 'lhs[%d]' % ilhs.index.position

  @varscope.when(IVar)
  def varscope(self, ivar):
    return '_%s[%d]' % (ivar.vid, ivar.index.position)

  @varscope.when(IBind)
  def varscope(self, ibind):
    raise RuntimeError('IBind not handled')

  @varscope.when(IFree)
  def varscope(self, ifree):
    raise RuntimeError('IFree not handled')

  # Expression.
  @dispatch.on('expression')
  def expression(self, expression):
    raise RuntimeError('unhandled Expression: %s' % type(expression))

  @expression.when(collections.Sequence)
  def expression(self, seq):
    return map(self.expression, seq)

  @expression.when(Exempt)
  def expression(self, exempt):
    pass

  @expression.when(Reference)
  def expression(self, exempt):
    pass

  @expression.when(Applic)
  def expression(self, applic):
    # FIXME - Needs symbol lookup.
    return 'Node(%s, %s)' % (self.closure[applic.ident], self.expression(applic.args))

  @expression.when(PartApplic)
  def expression(self, partapplic):
    pass

  @expression.when(IOr)
  def expression(self, ior):
    # FIXME - Needs symbol lookup.
    choice = self.closure['Prelude.Choice']
    return 'Node(%s, [%s, %s])' % (choice, self.expression(ior.lhs), self.expression(ior.rhs))

  @expression.when(BuiltinVariant)
  def expression(self, value):
    return repr(value)

  # Statement.
  @dispatch.on('statement')
  def statement(self, statement):
    raise RuntimeError('unhandled Statement: %s' % type(statement))

  @statement.when(IExternal)
  def statement(self, iexternal):
    pass

  @statement.when(Comment)
  def statement(self, comment):
    pass

  @statement.when(Declare)
  def statement(self, declare):
    vid = declare.var.vid
    scope = declare.var.scope
    return '_%s = %s' % (vid, self.varscope(scope))

  @statement.when(Assign)
  def statement(self, assign):
    pass

  @statement.when(Fill)
  def statement(self, fill):
    pass

  @statement.when(Return)
  def statement(self, return_):
    return 'return %s' % self.expression(return_.expr)

  @statement.when(ATable)
  def statement(self, atable):
    pass

  @statement.when(BTable)
  def statement(self, btable):
    pass



