from ... import graph
from .....utility.strings import ensure_str
import array, sys

__all__ = ['_biGenerator', '_biString', 'codepoints', 'pystring', 'text']

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
    item = rts.expr(item)
    # The item is built now, after set_goal walked the goal.  A free variable
    # made outside this evaluation (a curry.free marker used before) is new
    # to the variable table.  See rts_freevars.register_freevars.
    if rts.istate.external_freevars:
      rts.register_freevars(item)
    yield rts.prelude.Cons
    yield item
    yield graph.Node(rts.prelude._biGenerator, gen.target)

# A Char is a Unicode code point.  A string literal is kept as a memoryview of
# 4-byte code points: a slice of a memoryview costs O(1), so _biString walks a
# long string one character at a time.
CODEPOINT_FORMAT = next(
    code for code in 'IL' if array.array(code).itemsize == 4
  )
_UTF32 = 'utf-32-le' if sys.byteorder == 'little' else 'utf-32-be'

def codepoints(string):
  '''The code points of a Python string as a memoryview of 4-byte integers.'''
  return memoryview(ensure_str(string).encode(_UTF32)).cast(CODEPOINT_FORMAT)

def text(memory):
  '''The Python string held by a memoryview that ``codepoints`` made.'''
  return ''.join(map(chr, memory))

# Convert a Python string to a Curry string.
def pystring(rts, string):
  return graph.Node(rts.prelude._biString, codepoints(string))

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

