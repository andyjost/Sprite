'''
Implementation of the Prelude externals.
'''
from . import analysis
from . import conversions
from . import runtime
import itertools
import logging

logger = logging.getLogger(__name__)

def apply(interpreter, partapplic, arg):
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

def failed(interpreter):
  # FIXME: this should be a sequence of args to Node.__new__
  return ['node(%s)' % interpreter.closure['_System.Failure']]

def error(interpreter, msg):
  msg = str(conversions.topython(interpreter, msg))
  raise RuntimeError(msg)

def compare_impl(interpreter, a, b):
  a_boxed, b_boxed = (hasattr(x, 'info') for x in [a,b])
  assert a_boxed == b_boxed # cannot mix boxed and unboxed
  if not a_boxed:
    return -1 if a < b else 1 if a > b else 0
  a,b = map(interpreter.hnf, [a,b])
  assert all(isinstance(x, runtime.Node) for x in [a,b])
  assert all(runtime.T_CTOR <= x.info.tag for x in [a,b])
  if a.info.tag != b.info.tag:
    return -1 if a_val < b_val else 1
  else:
    for x, y in itertools.izip(a.successors, b.successors):
      z = compare_impl(interpreter, x, y)
      if z:
        return z
    return 0

def compare(interpreter, a, b):
  index = compare_impl(interpreter, a, b)
  info = interpreter.type('Prelude.Ordering')[index+1]
  yield info

def compose_io(interpreter, io_a, f):
  io_a = interpreter.hnf(io_a)
  yield interpreter.symbol('Prelude.apply').info
  yield f
  yield conversions.unbox(interpreter, io_a)

def return_(interpreter, a):
  yield interpreter.symbol('Prelude.IO').info
  yield a

def putChar(interpreter, a):
  interpreter.stdout.write(conversions.unbox(interpreter, a))
  yield interpreter.ni_IO
  yield runtime.Node(interpreter.ni_Unit);

def apply_hnf(interpreter, f, a):
  a = interpreter.hnf(a)
  yield interpreter.symbol('Prelude.apply').info
  yield f
  yield a

def apply_nf(interpreter, f, a):
  a = interpreter.nf(a)
  yield interpreter.symbol('Prelude.apply').info
  yield f
  yield a

def ensureNotFree(interpreter, a):
  a = interpreter.hnf(a)
  # FIXME: suspend is not implemented.
  if analysis.isa_freevar(interpreter, a):
    logging.warn('free variable in ensureNotFree but cannot suspend')
  yield interpreter.ni_Fwd
  yield a

  
