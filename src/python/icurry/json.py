from __future__ import absolute_import

from . import types
from ..utility.fmap import fmap
from ..utility.visitation import dispatch
import collections, json, traceback

def uni2str(arg):
  try:
    return arg.encode('utf-8')
  except:
    return arg

def _object_hook(kwds):
  try:
    clsname = kwds.pop('__class__')
  except KeyError:
    return kwds

  try:
    cls = types.__dict__[clsname]
  except KeyError:
    raise TypeError('No ICurry class named %s was found' % clsname)

  try:
    kwds = fmap(uni2str, kwds)
    return cls(**kwds)
  except Exception:
    raise TypeError(
        'Cannot construct %s.%s from arguments %r: %s'
            % (cls.__module__, cls.__name__, kwds, traceback.format_exc())
      )

def get_decoder():
  return json.JSONDecoder(object_hook=_object_hook)

def loads(json, decoder=get_decoder()):
  '''Load ICurry encoded as JSON.'''
  icurry = decoder.decode(json)
  return icurry

def load(file, decoder=get_decoder()):
  if isinstance(file, str):
    with open(file, 'rb') as istream:
      return loads(istream.read())
  else:
    return loads(file.read())

def get_encoder():
  return Encoder()

class Encoder(json.JSONEncoder):
  @dispatch.on('obj')
  def default(self, obj):
    print obj
    return json.JSONEncoder.encode(self, obj)

  EXCLUDED = {'filename'}

  @default.when(types.IObject)
  def default(self, iobj):
    data = collections.OrderedDict()
    data['__class__'] = type(iobj).__name__
    for k in getattr(iobj, '_fields_', iobj.__dict__):
      if k not in self.EXCLUDED:
        v = getattr(iobj, k)
        data[k] = v
    return data

def dumps(icurry, encoder=get_encoder()):
  json = encoder.encode(icurry)
  return json

def dump(icurry, file, encoder=get_encoder()):
  if isinstance(file, str):
    with open(file, 'w') as ostream:
      ostream.write(dumps(icurry, encoder))
  else:
    file.write(dumps(icurry, encoder))

