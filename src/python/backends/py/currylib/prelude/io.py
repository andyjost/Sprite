from .....exceptions import MonadError
from ... import graph
from . import show, string
import mmap, os

__all__ = [
    'appendFile', 'bindIO', 'catch', 'getChar', 'ioError', 'putChar'
  , 'readFile', 'returnIO', 'seqIO', 'writeFile'
  ]

def appendFile(rts, func):
  return writeFile(func, 'w+')

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
    yield rts.prelude._Fwd
    yield func.successors[0]

def getChar(rts):
  yield rts.prelude.Char
  yield rts.stdin.read(1)

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
  yield rts.prelude._PyGenerator
  def generator():
    with open(filename, 'r') as istream:
      for byte in mmap.mmap(istream.fileno(), 0, access=mmap.ACCESS_READ):
        yield byte
  yield generator()

def returnIO(rts, _0):
  yield rts.prelude.IO
  yield _0.successors[0]

def seqIO(rts, lhs):
  _1 = rts.variable(lhs, 0)
  _1.hnf()
  yield rts.prelude._Fwd
  yield lhs.successors[1]

def writeFile(rts, func, mode='w'):
  filename, data = func.successors
  filename = rts.topython(filename)
  List = getattr(rts.prelude, '.types')['[]']
  Char = getattr(rts.prelude, '.types')['Char']
  with open(filename, 'w') as ostream:
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

