'''
Implementation of the Prelude externals.
'''
from ..exceptions import *
from . import conversions
from .. import icurry
from . import runtime
import itertools
import logging
import operator

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

class Comparison(object):
  '''Implements ==, =:=, and Prelude.compare.'''
  def __init__(self, compare, resultinfo, conjunction):
    # A comparison function.  It behaves like ``cmp``, and so returns 0 (or
    # False) for "equal."  It must work on all primitive types (int, float,
    # and char) and node tags.
    self.compare = compare
    # A function taking the results of ``compare`` to node info.
    self.resultinfo = resultinfo
    # The conjunction used to combine terms when recursing.
    self.conjunction = conjunction

  def __call__(self, interp, root):
    lhs, rhs = (interp.hnf(root, [i]) for i in (0,1))
    lhs_isnode, rhs_isnode = (hasattr(x, 'info') for x in root)
    assert lhs_isnode == rhs_isnode # mixing boxed/unboxed -> type error
    if lhs_isnode:
      ltag, rtag = lhs.info.tag, rhs.info.tag
      index = self.compare(ltag, rtag)
      if not index: # recurse when the comparison returns 0 or False.
        arity = lhs.info.arity
        assert arity == rhs.info.arity
        if arity:
          conj = self.conjunction(interp)
          terms = (runtime.Node(root.info, l, r) for l,r in zip(lhs, rhs))
          expr = reduce((lambda a,b: runtime.Node(conj, a, b)), terms)
          yield expr.info
          for succ in expr:
            yield succ
          return
    else:
      index = self.compare(lhs, rhs) # Unboxed comparison.
    yield self.resultinfo(interp, index)

compare = Comparison( # compare
    compare=cmp
  , resultinfo=lambda interp, index:
        interp.type('Prelude.Ordering').constructors[index+1]
  , conjunction=lambda interp: interp.prelude.compare_conjunction
  )

equals = Comparison( # ==
    compare=operator.ne # False means equal.
  , resultinfo=lambda interp, index:
        interp.prelude.False if index else interp.prelude.True
  , conjunction=lambda interp: getattr(interp.prelude, '&&')
  )

equal_constr = Comparison( # =:=
    compare=operator.ne # False means equal.
  , resultinfo=lambda interp, index:
        interp.prelude._Failure if index else interp.prelude.True
  , conjunction=lambda interp: getattr(interp.prelude, '&&')
  )

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
