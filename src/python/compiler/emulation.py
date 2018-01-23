'''
A pure-Python Curry emulator.
'''

from .icurry import *
from .visitation import dispatch
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
InfoTable = collections.namedtuple('InfoTable', ['name', 'arity', 'show'])

class TypeInfo(object):
  '''Compile-time type info.'''
  def __init__(self, info):
    self.info = info

  def check_call(self, args):
    if len(args) != self.info.arity:
      raise TypeError(
          '"%s" takes %d args, not %d' % (self.info.name, self.info.arity, len(args))
        )
    # TODO: Add type checking

  def construct(self, *args):
    self.check_call(args)
    return Node(self.info, args)


class Node(object):
  ''' A node in an expression.'''
  def __new__(cls, info, args):
    self = object.__new__(cls)
    self.info = info
    self.args = args
    return self

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
    info = InfoTable(icons.ident.basename, icons.arity, ctor_show)
    setattr(emmodule, icons.ident.basename, TypeInfo(info))

  @__compile_impl.when(IFunction)
  def __compile_impl(self, ifun, emmodule):
    setattr(emmodule, ifun.ident.basename, ifun) # FIXME: put an impl, not ICurry, here.

  # Expression building.
  # ====================
  @dispatch.on('arg')
  def build(self, arg, *args):
    raise RuntimeError('unhandled argument type')

  @build.when(numbers.Integral)
  def build(self, arg, *args):
    ti_int.check_call(args)
    return Node(ti_int.info, [int(arg)])

  @build.when(numbers.Real)
  def build(self, arg, *args):
    ti_float.check_call(args)
    return Node(ti_float.info, [float(arg)])

  @build.when(TypeInfo)
  def build(self, info, *args):
    return info.construct(*map(self.build, args))

  @build.when(Node)
  def build(self, node):
    return node

# Misc.
# =====
def show_gen(node, xform):
  yield node.info.name
  for arg in node.args:
    yield xform(arg)

@dispatch.on('arg')
def ctor_show(arg):
  return str(arg)

@ctor_show.when(Node)
def ctor_show(node):
  return ' '.join(show_gen(node, ctor_show_inner))

@dispatch.on('arg')
def ctor_show_inner(arg):
  return str(arg)

@ctor_show_inner.when(Node)
def ctor_show_inner(node):
  if len(node.args) > 1:
    return '(%s)' % ctor_show(node)
  else:
    return ctor_show(node)

def show_value(node):
  assert len(node.args) == 1
  return str(node.args[0])


# Built-in types.
# ===============
ti_int = TypeInfo(InfoTable('Int', 0, show_value))
ti_float = TypeInfo(InfoTable('Float', 0, show_value))

