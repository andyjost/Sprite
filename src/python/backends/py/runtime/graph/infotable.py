from ..... import context
import types
import weakref

class InfoTable(object):
  '''
  Runtime info for a node.  Every Curry node stores an `InfoTable`` instance,
  which contains instance-independent data.
  '''
  # Constructor flags.
  INT_TYPE       = 0x1 # Prelude.Int
  CHAR_TYPE      = 0x2 # Prelude.Char
  FLOAT_TYPE     = 0x3 # Prelude.Float
  BOOL_TYPE      = 0x4 # Constructor of Prelude.Bool
  LIST_TYPE      = 0x5 # Constructor of Prelude.List
  TUPLE_TYPE     = 0x6 # Constructor of Prelude.() et. al
  IO_TYPE        = 0x7 # Constructor of Prelude.IO
  PARTIAL_TYPE   = 0x8 # A partial application
  # Function flags.
  MONADIC = 0x9 # Whether any monadic function can be reached.

  __slots__ = ['name', 'arity', 'tag', '_step', 'format', 'typecheck', 'typedef', 'flags']
  def __init__(self, name, arity, tag, step, format, typecheck, flags):
    # The node name.  Normally the constructor or function name.
    self.name = name
    # Arity.
    self.arity = arity
    # Node kind tag.
    self.tag = tag
    # The step function.  For functions, this is the function called to perform
    # a computational step at this node.
    self._step = step
    # Describes the node format.  It must have a ``format`` method, which will
    # be passed the node name followed by its rendered arguments.
    self.format = format
    # Used in debug mode to verify argument types.  The frontend typechecks
    # generated code, but this is helpful for checking the hand-written code
    # implementing built-in functions.
    self.typecheck = typecheck
    # The type that this constructor belongs to.  This is needed at runtime to
    # implement =:=, when a free variable must be bound to an HNF.  It could be
    # improved to use just a runtime version of the typeinfo.
    self.typedef = None
    self.flags = flags

  @property
  def is_special(self):
    return self.flags & 0xf

  @property
  def is_primitive(self):
    return (self.flags & 0xf) in [self.INT_TYPE, self.CHAR_TYPE, self.FLOAT_TYPE]

  @property
  def is_int(self):
    return (self.flags & 0xf) == self.INT_TYPE

  @property
  def is_char(self):
    return (self.flags & 0xf) == self.CHAR_TYPE

  @property
  def is_float(self):
    return (self.flags & 0xf) == self.FLOAT_TYPE

  @property
  def is_bool(self):
    return (self.flags & 0xf) == InfoTable.BOOL_TYPE

  @property
  def is_list(self):
    return (self.flags & 0xf) == InfoTable.LIST_TYPE

  @property
  def is_tuple(self):
    return (self.flags & 0xf) == InfoTable.TUPLE_TYPE

  @property
  def is_io(self):
    return (self.flags & 0xf) == InfoTable.IO_TYPE

  @property
  def is_partial(self):
    return (self.flags & 0xf) == InfoTable.PARTIAL_TYPE

  @property
  def is_monadic(self):
    return self.flags & InfoTable.MONADIC

  @property
  def step(self):
    # The step function can either be a function or a tuple (f, a, b, ...).  If
    # the latter, then f(a, b, ...) is called to get the actual step function
    # the first time it is accessed.  LazyFunction is a tuple that omits lengthy
    # details from the representation.
    if isinstance(self._step, tuple):
      self._step = self._step[0](*self._step[1:])
    return self._step

  @step.setter
  def step(self, value):
    self._step = value

  def __str__(self):
    return 'Info for %r' % self.name

  def __repr__(self):
    return ''.join([
        'InfoTable('
      , ', '.join('%s=%s' % (
            slot, self._showslot(getattr(self, slot))) for slot in self.__slots__
          )
      , ')'
      ])

  def _showslot(self, x):
    if isinstance(x, weakref.ref):
      return repr(x())
    else:
      return repr(x)

context.InfoTable.register(InfoTable)

