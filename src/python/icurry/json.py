from __future__ import absolute_import

from collections import Mapping, Sequence
from . import types
from ..utility.visitation import dispatch
import json
import traceback as traceback

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
    clsname = kwds.pop('__class__')
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

def parse(data, decoder=get_decoder()):
  '''Parse ICurry encoded as JSON.'''
  json = decoder.decode(data)
  return postprocess(json)

def postprocess(imodule):
  assert isinstance(imodule, types.IModule)
  if '.' in imodule.fullname:
    parts = imodule.fullname.split('.')
    for iend in reversed(range(1, len(parts))):
      pkgname = '.'.join(parts[:iend])
      imodule = types.IPackage(pkgname, [imodule])
  return imodule
