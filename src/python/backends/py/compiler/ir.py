__all__ = ['IR']

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
  def dump(self, stream=None):
    stream.write(self.dump())

  @dump.when(type(None))
  def dump(self, _=None):
    from . import render
    return render.render(self)

  @dump.when(six.string_types)
  def dump(self, filename=None):
    with open(filename, 'w') as out:
      self.dump(out)


  def __repr__(self):
    return '<Python IR for %r>' % icurry.name

