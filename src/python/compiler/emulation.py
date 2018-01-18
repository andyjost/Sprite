'''
A pure-Python Curry emulator.
'''

from .icurry import *
from .visitation import dispatch
import collections
import logging
import types

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG
  , format='%(asctime)s [%(levelname)s] %(message)s'
  , datefmt='%m/%d/%Y %H:%M:%S'
  )
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

  # import_
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


  # compile
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
    # TODO: functions
    return emmodule

  @__compile_impl.when(IConstructor)
  def __compile_impl(self, icons, emmodule):
    setattr(emmodule, icons.ident.basename, icons)

