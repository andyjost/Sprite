from ......exceptions import MonadError
from ... import graph

try:
  import mmap
except ImportError:
  mmap = None

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
        rts.prelude.IOError.info.typedef().constructors[idx]
      , rts.expr(iter(str(exc)))
      )
  else:
    yield rts.prelude._Fwd
    yield func.successors[0]

def getChar(rts):
  yield rts.prelude.Char
  yield rts.stdin.read(1)

def ioError(rts, func):
  yield rts.prelude.error
  yield graph.Node(rts.prelude.show, func.successors[0])

def putChar(rts, a):
  rts.stdout.write(a.unboxed_value)
  yield rts.prelude.IO
  yield graph.Node(rts.prelude.Unit)

def readFile(rts, filename):
  filename = rts.topython(filename.target)
  stream = open(filename, 'r')
  if mmap is None:
    def generateBytes():
      while True:
        chunk = stream.read(chunksize)
        if not chunk:
          return
        for byte in chunk:
          yield byte
    gen = generator()
  else:
    gen = iter(mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ))
  yield rts.prelude._PyGenerator
  yield gen

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
  stream = open(filename, 'w')
  List = rts.prelude.Cons.typedef()
  Char = rts.prelude.Char.typedef()
  while True:
    _1 = rts.variable(func, 1)
    _1.hnf(typedef=List)
    tag = _1.info.tag
    if tag == 0: # Cons
      char = rts.variable(_1, 0)
      char.hnf(typedef=Char)
      stream.write(char.unboxed_value)
      func.successors[1] = _1.successors[1]
    else:        # Nil
      assert tag == 1
      yield rts.prelude.IO
      yield graph.Node(rts.prelude.Unit)
      break

