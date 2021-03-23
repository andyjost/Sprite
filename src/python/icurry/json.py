from __future__ import absolute_import

from collections import Mapping, Sequence
from . import types
from ..utility.visitation import dispatch
import json

@dispatch.on('arg')
def fmap(f, arg):
  return f(arg)

@fmap.when(Sequence, no=(basestring,))
def fmap(f, arg):
  return type(arg)(fmap(f, x) for x in arg)

@fmap.when(Mapping)
def fmap(f, arg):
  return type(arg)((fmap(f, k), fmap(f, v)) for k,v in arg.items())

def uni2str(arg):
  try:
    return arg.encode('utf-8')
  except:
    return arg

def _object_hook(kwds):
  try:
    cls = kwds.pop('__class__')
    return types.__dict__[cls](**fmap(uni2str, kwds))
  except:
    import code
    code.interact(local=dict(globals(), **locals()))

def get_decoder():
  return json.JSONDecoder(object_hook=_object_hook)

def parse(data, decoder=get_decoder()):
  '''Parse ICurry encoded as JSON.'''
  return decoder.decode(data)

