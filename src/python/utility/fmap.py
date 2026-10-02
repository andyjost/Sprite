from . import visitation
import collections.abc

@visitation.dispatch.on('arg')
def fmap(f, arg):
  return f(arg)

@fmap.when(collections.abc.Sequence, no=(str,))
def fmap(f, arg):
  return type(arg)(fmap(f, x) for x in arg)

@fmap.when(collections.abc.Mapping)
def fmap(f, arg):
  return type(arg)((fmap(f, k), fmap(f, v)) for k,v in arg.items())

