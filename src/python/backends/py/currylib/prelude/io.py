from .....exceptions import EvaluationError, CurryIOError, NondetError, IntOverflowError
from ... import graph
from . import show, string

__all__ = [
    'appendFile', 'bindIO', 'catch', 'getChar', 'ioError', 'putChar'
  , 'readFile', 'returnIO', 'seqIO', 'writeFile'
  ]

def appendFile(rts, func):
  return writeFile(rts, func, 'a')

def bindIO(rts, lhs):
  io_a = rts.variable(lhs, 0)
  io_a.hnf()
  a = rts.variable(io_a, 0)
  yield rts.prelude.apply
  yield lhs.successors[1]
  yield a

def catch(rts, func):
  try:
    _1 = rts.variable(func, 0)
    _1.hnf()
  except (OSError, EvaluationError, IntOverflowError) as exc:
    yield rts.prelude.apply
    yield func.successors[1]
    idx = getattr(exc, 'CTOR_INDEX', 0)
    message = getattr(exc, 'curry_message', str(exc))
    if isinstance(exc, OSError) and not isinstance(exc, CurryIOError):
      message = exc.strerror
      if exc.filename is not None:
        message += ': ' + exc.filename
    yield graph.Node(
        rts.prelude.IOError.info.typedef.constructors[idx]
      , string.pystring(rts, message)
      )
  else:
    yield rts.Fwd
    yield func.successors[0]

def getChar(rts):
  yield rts.prelude.IO
  yield graph.Node(rts.prelude.Char, rts.stdin.read(1))

def ioError(rts, func):
  value = rts.variable(func, 0)
  value.hnf()
  index = value.info.tag
  message = ''.join(rts.topython(value.successors[0]))
  prefix = ('i/o error', 'user error', 'failed computation', 'nondet error')[index]
  cls = NondetError if index == 3 else CurryIOError
  error = cls('%s: %s' % (prefix, message))
  error.CTOR_INDEX = index
  error.curry_message = message
  raise error

def putChar(rts, a):
  rts.stdout.write(a.unboxed_value)
  yield rts.prelude.IO
  yield graph.Node(rts.prelude.Unit)

def readFile(rts, filename):
  filename = rts.topython(filename.target)
  # Read the file now, so that an error is raised while the action executes
  # (and ``catch`` can handle it).  The file holds UTF-8: each code point
  # becomes one character, and a malformed byte sequence becomes the
  # replacement character, as in PAKCS.  An empty file gives the empty string.
  with open(filename, 'rb') as istream:
    data = istream.read()
  yield rts.prelude.IO
  yield string.pystring(rts, data.decode('utf-8', 'replace'))

def returnIO(rts, _0):
  yield rts.prelude.IO
  yield _0.successors[0]

def seqIO(rts, lhs):
  _1 = rts.variable(lhs, 0)
  _1.hnf()
  yield rts.Fwd
  yield lhs.successors[1]

def writeFile(rts, func, mode='w'):
  '''
  Write a string to a file (``mode`` 'w') or append it ('a').

  The step runs again when the evaluation of the string is interrupted, for
  instance when the step budget rotates the queue.  The first entry truncates
  the file and then turns the node into ``prim_appendFile``, so a later entry
  appends to the characters already written.  The characters are written as
  UTF-8.
  '''
  filename = rts.topython(func.successors[0])
  List = getattr(rts.prelude, '.types')['[]']
  Char = getattr(rts.prelude, '.types')['Char']
  with open(filename, mode, encoding='utf-8') as ostream:
    if mode == 'w':
      func.rewrite(rts.prelude.prim_appendFile, *func.successors)
    while True:
      _1 = rts.variable(func, 1)
      _1.hnf(typedef=List)
      tag = _1.info.tag
      if tag == 0: # Cons
        char = rts.variable(_1, 0)
        char.hnf(typedef=Char)
        ostream.write(char.unboxed_value)
        func.successors[1] = _1.successors[1]
      else:        # Nil
        assert tag == 1
        yield rts.prelude.IO
        yield graph.Node(rts.prelude.Unit)
        break

