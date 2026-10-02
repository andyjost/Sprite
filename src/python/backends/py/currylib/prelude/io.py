from .....exceptions import MonadError
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
  except (IOError, MonadError) as exc:
    yield rts.prelude.apply
    yield func.successors[1]
    idx = getattr(exc, 'CTOR_INDEX', 0)
    yield graph.Node(
        rts.prelude.IOError.info.typedef.constructors[idx]
      , string.pystring(rts, str(exc))
      )
  else:
    yield rts.Fwd
    yield func.successors[0]

def getChar(rts):
  yield rts.prelude.IO
  yield graph.Node(rts.prelude.Char, rts.stdin.read(1))

def ioError(rts, func):
  yield rts.prelude.error
  showf = rts.symbol('Prelude._impl#show#Prelude.Show#Prelude.IOError')
  yield graph.Node(showf, func[0])

def putChar(rts, a):
  rts.stdout.write(a.unboxed_value)
  yield rts.prelude.IO
  yield graph.Node(rts.prelude.Unit)

def readFile(rts, filename):
  filename = rts.topython(filename.target)
  # Read the file now, so that an error is raised while the action executes
  # (and ``catch`` can handle it).  Each byte becomes one character, as in the
  # C++ backend.  An empty file gives the empty string.
  with open(filename, 'rb') as istream:
    data = istream.read()
  yield rts.prelude.IO
  yield string.pystring(rts, data)

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
  appends to the characters already written.
  '''
  filename = rts.topython(func.successors[0])
  List = getattr(rts.prelude, '.types')['[]']
  Char = getattr(rts.prelude, '.types')['Char']
  with open(filename, mode) as ostream:
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

