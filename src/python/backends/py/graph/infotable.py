from .... import context
import weakref

class InfoTable(context.InfoTable):
  '''
  Runtime info for a node.  Every Curry node stores an `InfoTable`` instance,
  which contains instance-independent data.
  '''
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

  @staticmethod
  def create(owner, *args):
    return InfoTable(*args)

  @property
  def step(self):
    if hasattr(self._step, 'materialize'):
      self._step = self._step.materialize()
    return self._step

  @step.setter
  def step(self, value):
    self._step = value

