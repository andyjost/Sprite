__all__ = ['IR']

from ....utility import visitation

class IR(object):
  def __init__(self, icurry, closure, lines):
    '''
    The intermediate representation for compiled Python code.

    Parameters:
    -----------
      ``icurry``
        The ICurry for this IR.  Every IFunction body should be implemented as
        ILink.

      ``closure``
        Definitions used by the Python code.  This includes nodeinfo, typedefs,
        and value lists needed at runtime.  When materializing code, these must
        be available.

      ``lines``
        List-formatted Python code defining the compiled functions.
    '''
    self.icurry = icurry
    self.closure = closure
    self.lines = lines
    assert not any('\n' in line for line in lines)

  @visitation.dispatch.on('stream')
  def dump(self, stream):
    from . import render
    python_code = render.render(self)
    stream.write(python_code)

  @dump.when(basestring)
  def dump(self, filename):
    with open(filename, 'w') as out:
      self.dump(out)


  def __repr__(self):
    return '<Python IR for %r>' % icurry.name

