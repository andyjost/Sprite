__all__ = ['IR']

from six.moves import cStringIO as StringIO
from ....utility import visitation
import abc, six

class IR(abc.ABC):

  CODETYPE = 'generic'

  @abc.abstractmethod
  def render(self):
    pass

  def __init__(self, icurry, closure, lines):
    '''
    The intermediate representation for generated code.

    Args:
      icurry:
        The ICurry for this IR.  Every IFunction body should be implemented as
        ILink.

      closure:
        Definitions used by the code.  This includes nodeinfo, typedefs,
        and value lists needed at runtime.  When materializing code, these must
        be available.

      lines:
        List-formatted code defining the compiled functions.
    '''
    self.icurry = icurry
    self.closure = closure
    self.lines = lines
    assert not any('\n' in line for line in lines)

  @visitation.dispatch.on('stream')
  def dump(self, stream=None, goal=None):
    stream.write(self.dump(None, goal))

  @dump.when(type(None))
  def dump(self, _=None, goal=None):
    stream = StringIO()
    if hasattr(self, 'header'):
      stream.write(self.header())
    stream.write(self.render(goal=goal))
    return stream.getvalue()

  @dump.when(six.string_types)
  def dump(self, filename=None, goal=None):
    with open(filename, 'w') as out:
      self.dump(out, goal=goal)

  def __repr__(self):
    return '<%s IR for %r>' % (self.CODETYPE, self.icurry.name)

