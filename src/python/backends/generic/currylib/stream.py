'''The C++ primitive of Sprite.Stream.'''

from . import ModuleSpecification
from ....common import F_MONADIC

def unsupported(rts, root):
  raise NotImplementedError('Sprite.Stream requires the C++ backend')

class StreamSpecification(ModuleSpecification):
  NAME = 'Sprite.Stream'
  TYPES = []
  FUNCTIONS = [('primYield', 2, {'all.flags': F_MONADIC, 'py.rawfunc': unsupported})]
  IMPORTS = ['Prelude']
