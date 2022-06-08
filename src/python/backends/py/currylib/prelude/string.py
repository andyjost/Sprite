from ... import graph
from .....utility.strings import ensure_binary, ensure_str
import six

__all__ = ['_biGenerator', '_biString', 'pystring']

def _biGenerator(rts, gen):
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
    yield graph.Node(rts.prelude._biGenerator, gen.target)

# Convert a Python string to a Curry string.
def pystring(rts, string):
  memory = memoryview(ensure_binary(string))
  return graph.Node(rts.prelude._biString, memory)

if six.PY2:
  ensure_char = lambda x: x # memoryview element is a str
else:
  ensure_char = chr         # memoryview element is an integer

def _biString(rts, _1):
  '''
  Implements a Curry string efficiently as a Python memory view.
  '''
  mem = _1.target
  if mem:
    yield rts.prelude.Cons
    yield graph.Node(rts.prelude.Char, ensure_char(mem[0]))
    yield graph.Node(rts.prelude._biString, mem[1:])
  else:
    yield rts.prelude.Nil

