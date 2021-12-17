__all__ = ['IR']

from .... import config
from six.moves import cStringIO as StringIO
from ....utility import visitation
import six

class IR(object):
  def __init__(self, icurry, closure, lines):
    '''
    The intermediate representation for compiled Python code.

    Args:
      icurry:
        The ICurry for this IR.  Every IFunction body should be implemented as
        ILink.

      closure:
        Definitions used by the Python code.  This includes nodeinfo, typedefs,
        and value lists needed at runtime.  When materializing code, these must
        be available.

      lines:
        List-formatted Python code defining the compiled functions.
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
    from . import render
    stream = StringIO()
    stream.write('#!%s\n' % config.python_exe())
    stream.write(render.render(self, goal=goal))
    return stream.getvalue()

  @dump.when(six.string_types)
  def dump(self, filename=None, goal=None):
    with open(filename, 'w') as out:
      self.dump(out, goal=goal)

  def __repr__(self):
    return '<Python IR for %r>' % icurry.name

