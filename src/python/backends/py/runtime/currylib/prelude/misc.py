from ......exceptions import ExecutionError
from ... import graph

__all__ = ['choice', 'error', 'failed', 'not_used', '_PyGenerator']

def choice(rts, _0):
  yield rts.prelude._Choice
  yield next(rts.idfactory)
  yield _0.successors[0]
  yield _0.successors[1]

def error(rts, msg):
  msg = str(rts.topython(msg))
  raise ExecutionError(msg)

def failed(rts):
  return [rts.prelude._Failure]

def not_used(rts, _0):
  raise RuntimeError("function 'Prelude.%s' is not used by Sprite" % _0.info.name)

def _PyGenerator(rts, gen):
  '''Implements a Python generator as a Curry list.'''
  try:
    item = next(gen.target)
  except StopIteration:
    yield rts.prelude.Nil
  else:
    yield rts.prelude.Cons
    yield rts.expr(item)
    yield graph.Node(rts.prelude._PyGenerator, gen.target)
