import collections
from ... import icurry

__all__ = ['LazyFunction']

class LazyFunction(
    collections.namedtuple('LazyFunction', ['interp', 'ifun', 'extern'])
  ):
  '''
  Materializes a step function when ``materialize`` is called.  This improves
  execution times by only compiling the functions that are actually used.
  '''
  def __new__(cls, *args):
    self = super(LazyFunction, cls).__new__(cls, *args)
    return self
  def materialize(self):
    if isinstance(self.ifun.body, icurry.IMaterial):
      return self.ifun.body.function
    else:
      cc = self.interp.context.compiler
      ir = cc.compile(*self)
      return cc.materialize(
          self.interp
        , ir
        , debug=self.interp.flags['debug']
        , ifun=self.ifun
        )
  def __repr__(self):
    return '<not yet compiled>'

