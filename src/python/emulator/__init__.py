'''
A pure-Python Curry emulator.
'''

from __future__ import print_function
from ..compiler.icurry import *
from . import evaluator
from . import prelude
from .node import InfoTable, TypeInfo, Node
from .show import Show
from ..visitation import dispatch
import collections
import logging
import numbers
import types

# For export.
Prelude = prelude.Prelude

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG
  , format='%(asctime)s [%(levelname)s] %(message)s'
  , datefmt='%m/%d/%Y %H:%M:%S'
  )

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

  def __init__(self):
    self._prelude = self.import_(Prelude)

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
    return OrderedDict([
        (k, self.__compile_impl(v, *args, **kwds)) for k,v in mapping.iteritems()
      ])

  @__compile_impl.when(IModule)
  def __compile_impl(self, imodule, emmodule):
    self.__compile_impl(imodule.types, emmodule)
    self.__compile_impl(imodule.functions, emmodule)
    return emmodule

  @__compile_impl.when(IConstructor)
  def __compile_impl(self, icons, emmodule):
    info = InfoTable(
        icons.ident.basename, icons.arity, evaluator.ctor_step
      , Show(icons.format)
      )
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
    args = (int(arg),) + args
    self._prelude.Int._check_call(args)
    return Node(self._prelude.Int.info, args)

  @expr.when(numbers.Real)
  def expr(self, arg, *args):
    args = (float(arg),) + args
    self._prelude.Float._check_call(args)
    return Node(self._prelude.Float.info, args)

  @expr.when(TypeInfo)
  def expr(self, info, *args):
    return info(*map(self.expr, args))

  @expr.when(Node)
  def expr(self, node):
    return node

  # Evaluating.
  # ===========
  def eval(self, goal, sink=print):
    evaluator.Evaluator(goal, sink).run()

