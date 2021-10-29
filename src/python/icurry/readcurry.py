from . import types
from ..utility.fmap import fmap
from ..utility import maxrecursion, readcurry as rc, visitation

__all__ = ['load', 'loads']

class Decoder(object):
  '''
  Decode the `readcurry` representation of ICurry into Python ICurry.
  '''
  @visitation.dispatch.on('arg')
  def decode(self, arg):
    raise TypeError('not handled: %r' % arg)

  @decode.when(rc.Identifier)
  def decode(self, ident):
    return getattr(types, ident.name)

  @decode.when(rc.Applic)
  def decode(self, applic):
    ty = self.decode(applic.f)
    args = fmap(self.decode, applic.args)
    return self.apply(ty, *args)

  @decode.when(types.IUnboxedLiteral)
  def decode(self, arg):
    return arg

  # Types in need of special processing to convert name triples into dotted
  # qualified names.
  QNAME_TYPES = (
      types.ICall, types.IConsBranch, types.IFunction, types.IConstructor
    )

  LITERAL_TYPES = types.IChar, types.IFloat, types.IInt

  def apply(self, ty, *args):
    if issubclass(ty, types.IDataType):
      (qual, name, _), ctors = args
      symbolname = '%s.%s' % (qual, name)
      ctors = [self.apply(types.IConstructor, *ctor) for ctor in ctors]
      return ty(symbolname, ctors)
    elif issubclass(ty, self.QNAME_TYPES):
      qual, name, _ = args[0]
      symbolname = '%s.%s' % (qual, name)
      return ty(symbolname, *args[1:])
    else:
      return ty(*args)

def loads(rcdata, decoder=Decoder()):
  '''Load ICurry encoded as readcurry.'''
  with maxrecursion():
    icurry = decoder.decode(rcdata)
  return icurry

def load(file, decoder=Decoder()):
  '''Load ICurry from an .icy file.'''
  if isinstance(file, str):
    with open(file, 'r') as istream:
      text = istream.read()
  else:
    text = file.read()
  rcdata = rc.parse(text)
  return loads(rcdata, decoder)

