__all__ = ['IR']

import abc

class IR(abc.ABC):

  CODETYPE = 'generic'

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

  def __repr__(self):
    return '<%s IR for %r>' % (self.CODETYPE, self.icurry.name)

