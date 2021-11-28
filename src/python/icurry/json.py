from __future__ import absolute_import

from . import types
from ..utility.fmap import fmap
from ..utility.strings import ensure_str_safe, ensure_str
from ..utility.visitation import dispatch
import collections, json, traceback

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
    kwds = fmap(ensure_str_safe, kwds)
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
  icurry = decoder.decode(ensure_str(json))
  return icurry

def load(file, decoder=get_decoder()):
  if isinstance(file, str):
    with open(file, 'r') as istream:
      data = istream.read()
    return loads(data)
  else:
    return loads(file.read())

def get_encoder():
  return Encoder()

class Encoder(json.JSONEncoder):
  @dispatch.on('obj')
  def default(self, obj):
    return json.JSONEncoder.encode(self, obj)

  # These mapping
  KEY_MAP = {
      'filename'  : None
    , 'fullname'  : 'name'
    , 'IModule'   : 'IProg'
    , 'IDataType' : 'IType'
    , 'symbolname': 'name'
  }

  VALUE_MAP = {
      'functions': lambda v: list(v.values())
    , 'imports'  : lambda v: list(v)
    , 'types'    : lambda v: list(v.values())
  }

  @default.when(types.IObject)
  def default(self, iobj):
    data = collections.OrderedDict()
    clsname = type(iobj).__name__
    data['__class__'] = self.KEY_MAP.get(clsname, clsname)
    for k in getattr(iobj, '_fields_', iobj.__dict__):
      v = getattr(iobj, k)
      vmapper = self.VALUE_MAP.get(k)
      k = self.KEY_MAP.get(k, k)
      if k is not None:
        if vmapper is not None:
          v = vmapper(v)
        data[k] = v
    return data

def dumps(icurry, encoder=get_encoder()):
  json = encoder.encode(icurry)
  return ensure_str(json)

def dump(icurry, file, encoder=get_encoder()):
  if isinstance(file, str):
    with open(file, 'w') as ostream:
      ostream.write(dumps(icurry, encoder))
  else:
    file.write(dumps(icurry, encoder))

