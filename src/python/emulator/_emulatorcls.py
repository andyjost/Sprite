'''
A pure-Python Curry emulator.
'''

from __future__ import print_function
from ..compiler.icurry import *
from ..visitation import dispatch
import collections
import logging
import numbers
import types

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG
  , format='%(asctime)s [%(levelname)s] %(message)s'
  , datefmt='%m/%d/%Y %H:%M:%S'
  )

# Type Info.
# ==========
# Run-time type info.
InfoTable = collections.namedtuple('InfoTable', ['name', 'arity', 'step', 'show'])

class TypeInfo(object):
  '''Compile-time type info.'''
  def __init__(self, info):
    self.info = info

  def _check_call(self, args):
    if len(args) != self.info.arity:
      raise TypeError(
          'cannot construct "%s" (arity=%d), with %d args'
              % (self.info.name, self.info.arity, len(args))
        )

  def __call__(self, *args):
    '''Constructs an object of this type.'''
    self._check_call(args)
    return Node(self.info, args)


class Node(object):
  ''' A node in an expression.'''
  def __new__(cls, info, args):
    self = object.__new__(cls)
    self.info = info
    self.args = args
    return self

  def __eq__(self, rhs):
    return self.info == rhs.info and self.args == rhs.args

  def __ne__(self, rhs):
    return not (self == rhs)

  def __str__(self):
    return self.info.show(self)

  def __repr__(self):
    return '<%s %s>' % (self.info.name, self.args)


# Emulation.
# ==========
class Emulator(object):
  '''
  Implements a Curry emulator.

  Use ``import_`` to add modules to the system.  Then use ``eval`` to evaluate
  expressions.
  '''
  def __new__(cls):
    self = object.__new__(cls)
    self.modules = {}
    return self

  # Importing.
  # ==========
  @dispatch.on('arg')
  def import_(self, arg):
    raise RuntimeError('unhandled argument type')

  @import_.when(collections.Sequence)
  def import_(self, seq):
    return [self.import_(item) for item in seq]

  @import_.when(IModule)
  def import_(self, imodule):
    if imodule.name not in self.modules:
      self.modules[imodule.name] = self.compile(imodule)
    return self.modules[imodule.name]

  # Compiling.
  # ============
  def compile(self, imodule):
    assert isinstance(imodule, IModule)
    emmodule = types.ModuleType(imodule.name)
    return self.__compile_impl(imodule, emmodule)

  @dispatch.on('node')
  def __compile_impl(self, node, emmodule):
    raise RuntimeError('unhandled node type')

  @__compile_impl.when(collections.Sequence)
  def __compile_impl(self, seq, *args, **kwds):
    return [self.__compile_impl(item, *args, **kwds) for item in seq]

  @__compile_impl.when(collections.Mapping)
  def __compile_impl(self, mapping, *args, **kwds):
    return OrderedDict([(k, self.__compile_impl(v, *args, **kwds)) for k,v in mapping.iteritems()])

  @__compile_impl.when(IModule)
  def __compile_impl(self, imodule, emmodule):
    self.__compile_impl(imodule.types, emmodule)
    self.__compile_impl(imodule.functions, emmodule)
    return emmodule

  @__compile_impl.when(IConstructor)
  def __compile_impl(self, icons, emmodule):
    info = InfoTable(icons.ident.basename, icons.arity, ctor_step, Show(icons.format))
    setattr(emmodule, icons.ident.basename, TypeInfo(info))

  @__compile_impl.when(IFunction)
  def __compile_impl(self, ifun, emmodule):
    setattr(emmodule, ifun.ident.basename, ifun) # FIXME: put an impl, not ICurry, here.

  # Expression building.
  # ====================
  @dispatch.on('arg')
  def expr(self, arg, *args):
    raise RuntimeError('unhandled argument type')

  @expr.when(collections.Sequence)
  def expr(self, arg):
    # Supports nested structures, e.g., Cons 0 [Cons 1 Nil].
    return self.expr(*arg)

  @expr.when(numbers.Integral)
  def expr(self, arg, *args):
    ti_int._check_call(args)
    return Node(ti_int.info, [int(arg)])

  @expr.when(numbers.Real)
  def expr(self, arg, *args):
    ti_float._check_call(args)
    return Node(ti_float.info, [float(arg)])

  @expr.when(TypeInfo)
  def expr(self, info, *args):
    return info(*map(self.expr, args))

  @expr.when(Node)
  def expr(self, node):
    return node

  # Evaluating.
  # ===========
  def eval(self, goal, sink=print):
    Evaluator(goal, sink).run()


# Emulator runtime.
# =================
class RewriteStepTaken(Exception):
  '''
  Raised after a rewrite step is taken.  Used to return control to the main
  evaluator loop.
  '''
  pass

class Evaluator(object):
  def __new__(cls, goal, sink):
    self = object.__new__(cls)
    self.sink = sink
    self.queue = [goal]
    return self

  def run(self):
    while self.queue:
      expr = self.queue.pop(0)
      try:
        is_value = expr.info.step(expr, NORMALIZE, self.sink)
        if is_value:
          self.sink(str(expr))
          self.sink('\n')
        # TODO: choice handled here?
        # else expr is a failure, so discard it.
      except RewriteStepTaken:
        self.queue.append(expr)

NORMALIZE = 0
HEADNORMALIZE = 1

def ctor_step(node, mode, sink):
  '''Step function for constructors.'''
  return all(
      arg.info.step(arg, mode, sink)
          for arg in node.args
          if isinstance(arg, Node)
    )

# Misc.
# =====
class Show(object):
  def __new__(cls, format=None):
    return format if callable(format) else object.__new__(cls, format)

  def __init__(self, format=None):
    self.format = getattr(format, 'format', None) # i.e., str.format.

  @dispatch.on('arg')
  def __call__(self, arg):
    return str(arg)

  @__call__.when(Node)
  def __call__(self, node):
    subexprs = self.generate(node, self._showinner)
    if self.format is None:
      return ' '.join(subexprs)
    else:
      subexprs = list(subexprs)
      return self.format(*subexprs)

  @staticmethod
  def generate(node, xform):
    yield node.info.name
    for arg in node.args:
      yield xform(arg)

  @dispatch.on('arg')
  def _showinner(self, arg):
    return str(arg)

  @_showinner.when(Node)
  def _showinner(self, node):
    show = node.info.show
    if len(node.args) > 1:
      return '(%s)' % show(node)
    else:
      return show(node)


# Built-in types.
# ===============
ti_int = TypeInfo(InfoTable('Int', 0, ctor_step, Show(format='{1}')))
ti_float = TypeInfo(InfoTable('Float', 0, ctor_step, Show(format='{1}')))
# ti_choice = TypeInfo(InfoTable('Choice', 2, choice_step, Show(format='{1} ? {2}')))

