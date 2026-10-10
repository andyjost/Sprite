from . import types
from ..utility import readcurry as rc
from ..utility.trampoline import trampoline

__all__ = ['load', 'loads']

class Decoder(object):
  '''
  Decode the `readcurry` representation of ICurry into Python ICurry.  The
  walk runs on a stack of its own (:func:`utility.trampoline.trampoline`),
  so a nested application of any depth needs no recursion (issue #125).
  '''
  def decode(self, arg):
    return trampoline(self._decode(arg))

  def _decode(self, arg):
    if isinstance(arg, rc.Identifier):
      return getattr(types, arg.name)
    elif isinstance(arg, rc.Applic):
      ty = getattr(types, arg.f.name)
      args = []
      for x in arg.args:
        x = yield self._decode(x)
        args.append(x)
      return self.apply(ty, *args)
    elif isinstance(arg, (list, tuple)):
      out = []
      for x in arg:
        x = yield self._decode(x)
        out.append(x)
      return type(arg)(out)
    elif isinstance(arg, types.IUnboxedLiteral):
      return arg
    raise TypeError('not handled: %r' % arg)

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
  return decoder.decode(rcdata)

def load(file, decoder=Decoder()):
  '''Load ICurry from an .icy file.'''
  if isinstance(file, str):
    with open(file, 'r', encoding='utf-8') as istream:
      text = istream.read()
  else:
    text = file.read()
  rcdata = rc.parse(text)
  return loads(rcdata, decoder)
