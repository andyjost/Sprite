from . import visitation
import collections

@visitation.dispatch.on('arg')
def fmap(f, arg):
  return f(arg)

@fmap.when(collections.Sequence, no=(basestring,))
def fmap(f, arg):
  return type(arg)(fmap(f, x) for x in arg)

@fmap.when(collections.Mapping)
def fmap(f, arg):
  return type(arg)((fmap(f, k), fmap(f, v)) for k,v in arg.items())

