'''
Implementation of the Prelude externals.
'''
from . import analysis
from . import conversions
from . import runtime
import itertools
import logging

logger = logging.getLogger(__name__)

def apply(interp, partapplic, arg):
  missing, term = partapplic # note: "missing" is unboxed.
  assert missing >= 1
  if missing == 1:
    yield term.info
    for t in term.successors:
      yield t
    yield arg
  else:
    yield partapplic.info
    yield missing-1
    yield runtime.Node(term.info, *(term.successors+[arg]), partial=True)

def failed(interp):
  return [interp.ni_Failure]

def error(interp, msg):
  msg = str(conversions.topython(interp, msg))
  raise RuntimeError(msg)

def compare_impl(interp, a, b):
  a_boxed, b_boxed = (hasattr(x, 'info') for x in [a,b])
  assert a_boxed == b_boxed # cannot mix boxed and unboxed
  if not a_boxed:
    return -1 if a < b else 1 if a > b else 0
  a,b = map(interp.hnf, [a,b])
  assert all(isinstance(x, runtime.Node) for x in [a,b])
  assert all(runtime.T_CTOR <= x.info.tag for x in [a,b])
  if a.info.tag != b.info.tag:
    return -1 if a_val < b_val else 1
  else:
    for x, y in itertools.izip(a.successors, b.successors):
      z = compare_impl(interp, x, y)
      if z:
        return z
    return 0

def compare(interp, a, b):
  index = compare_impl(interp, a, b)
  info = interp.type('Prelude.Ordering')[index+1]
  yield info

def compose_io(interp, io_a, f):
  io_a = interp.hnf(io_a)
  yield interp.symbol('Prelude.apply').info
  yield f
  yield conversions.unbox(interp, io_a)

def return_(interp, a):
  yield interp.symbol('Prelude.IO').info
  yield a

def putChar(interp, a):
  interp.stdout.write(conversions.unbox(interp, a))
  yield interp.ni_IO
  yield runtime.Node(interp.ni_Unit);

def apply_hnf(interp, f, a):
  a = interp.hnf(a)
  yield interp.symbol('Prelude.apply').info
  yield f
  yield a

def apply_nf(interp, f, a):
  interp.nf(a)
  yield interp.symbol('Prelude.apply').info
  yield f
  yield a

def apply_gnf(interp, f, a):
  interp.nf(a, ground=True)
  yield interp.symbol('Prelude.apply').info
  yield f
  yield a

def ensureNotFree(interp, a):
  a = interp.hnf(a)
  # FIXME: suspend is not implemented.
  if analysis.isa_freevar(interp, a):
    logging.warn('free variable in ensureNotFree but cannot suspend')
  yield interp.ni_Fwd
  yield a

def _python_generator_(interp, gen):
  '''Implements a Python generator as a Curry list.'''
  try:
    item = next(gen)
  except StopIteration:
    yield interp.ni_Nil
  else:
    yield interp.ni_Cons
    yield interp.expr(item)
    yield interp.expr(gen)

