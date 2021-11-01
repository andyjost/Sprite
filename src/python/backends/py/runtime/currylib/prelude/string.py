from ... import graph

__all__ = ['_PyGenerator', '_PyString', 'pystring']

def _PyGenerator(rts, gen):
  '''
  Implements a Python generator as a Curry list.  The generator is single-pass,
  so is not safe for general use.  This is used to implement IO actions.
  '''
  try:
    item = next(gen.target)
  except StopIteration:
    yield rts.prelude.Nil
  else:
    yield rts.prelude.Cons
    yield rts.expr(item)
    yield graph.Node(rts.prelude._PyGenerator, gen.target)

# Convert a Python string to a Curry string.
def pystring(rts, string):
  return graph.Node(rts.prelude._PyString, memoryview(string))

def _PyString(rts, _1):
  '''
  Implements a Curry string efficiently as a Python memory view.
  '''
  mem = _1.target
  if mem:
    yield rts.prelude.Cons
    yield mem[0]
    yield graph.Node(rts.prelude._PyString, mem[1:])
  else:
    yield rts.prelude.Nil

