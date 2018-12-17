'''
Implementation of the Prelude externals.
'''
from ..exceptions import *
from . import conversions
from . import runtime
import itertools
import logging
from .. import icurry

logger = logging.getLogger(__name__)

def apply(interp, lhs):
  interp.hnf(lhs, [0]) # normalize "partapplic"
  partapplic, arg = lhs
  missing, term = partapplic # note: "missing" is unboxed.
  assert missing >= 1
  if missing == 1:
    yield term
    for t in term.successors:
      yield t
    yield arg
  else:
    yield partapplic
    yield missing-1
    yield runtime.Node(term, *(term.successors+[arg]), partial=True)

def failed(interp):
  return [interp.prelude._Failure]

choice_id = itertools.count()

def choice(interp, lhs):
  yield interp.prelude._Choice
  yield next(interp._idfactory_)
  yield lhs[0]
  yield lhs[1]

def error(interp, msg):
  msg = str(interp.topython(msg))
  raise RuntimeError(msg)

def compare(interp, root):
  lhs, rhs = (interp.hnf(root, [i]) for i in (0,1))
  lhs_isboxed, rhs_isboxed = (hasattr(x, 'info') for x in root)
  assert lhs_isboxed == rhs_isboxed # mixing boxed/unboxed -> type error
  if lhs_isboxed:
    ltag, rtag = lhs.info.tag, rhs.info.tag
    index = -1 if ltag < rtag else 1 if ltag > rtag else 0
    if not index:
      arity = lhs.info.arity
      assert arity == rhs.info.arity
      if arity:
        conj = interp.prelude.compare_conjunction
        terms = (runtime.Node(root.info, l, r) for l,r in zip(lhs, rhs))
        expr = reduce((lambda a,b: runtime.Node(conj, a, b)), terms)
        yield expr.info
        for succ in expr:
          yield succ
        return
  else:
    index = -1 if lhs < rhs else 1 if lhs > rhs else 0
  info = interp.type('Prelude.Ordering').constructors[index+1]
  yield info

def compose_io(interp, lhs):
  io_a = interp.hnf(lhs, [0])
  yield interp.prelude.apply
  yield lhs[1]
  yield conversions.unbox(interp, io_a)

def return_(interp, a):
  yield interp.prelude.IO
  yield a

def putChar(interp, a):
  interp.stdout.write(conversions.unbox(interp, a))
  yield interp.prelude.IO
  yield runtime.Node(interp.prelude.Unit)

def getChar(interp):
  yield interp.prelude.Char
  yield interp.stdin.read(1)

def generateBytes(stream, chunksize=4096):
  with stream:
    while True:
      chunk = stream.read(chunksize)
      if not chunk:
        return
      for byte in chunk:
        yield byte

def readFile(interp, filename):
  filename = interp.topython(filename)
  stream = open(filename, 'r')
  try:
    import mmap
  except ImportError:
    gen = generateBytes(stream)
  else:
    gen = iter(mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ))
  return _python_generator_(interp, gen)

def apply_hnf(interp, root):
  yield interp.prelude.apply
  yield root[0]
  yield interp.hnf(root, [1])

def normalize(interp, root, path, ground):
  '''Used to implement $!! and $##.'''
  try:
    runtime.hnf(interp, root, path)
  except runtime.E_RESIDUAL:
    if ground:
      raise
    else:
      return root[path]
  target, freevars = runtime.N(interp, root, path=path)
  if ground and freevars:
    raise runtime.E_RESIDUAL(freevars)
  return target

def apply_nf(interp, root):
  yield interp.prelude.apply
  yield root[0]
  yield normalize(interp, root, [1], ground=False)

def apply_gnf(interp, root):
  yield interp.prelude.apply
  yield root[0]
  yield normalize(interp, root, [1], ground=True)

def ensureNotFree(interp, a):
  # This function does nothing when evaluated.  It is, however, a designated
  # symbol that is checked during pull_tabbing.  Pulling a choice past
  # ensureNotFree is an error.
  yield interp.prelude._Fwd
  yield a

def _python_generator_(interp, gen):
  '''Implements a Python generator as a Curry list.'''
  try:
    item = next(gen)
  except StopIteration:
    yield interp.prelude.Nil
  else:
    yield interp.prelude.Cons
    yield interp.expr(item)
    yield interp.expr(gen)
