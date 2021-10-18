'''
Code for synthesizing built-in functions.
'''

from ..... import inspect
from .. import ir, statics
from ...runtime.currylib.prelude.math import apply_unboxed
import operator as op

__all__ = ['synthesize_function']

def synthesize_function(*args, **kwds):
  '''
  Synthesize a special function, if possible, or return None.
  '''
  return compile_boxedfunc(*args, **kwds) or \
         compile_rawfunc(*args, **kwds) or \
         compile_unboxedfunc(*args, **kwds)

def compile_boxedfunc(interp, ifun, closure, entry):
  '''
  Compiles code for a built-in function.  See README.md.  Corresponds to the
  "py.boxedfunc" metadata.

  The Python implementation function must accept the arguments in head-normal
  form, but without any other preprocessing (e.g., unboxing).  It returns a
  sequence of arguments accepted by ``runtime.Node.__new__``.
  '''
  boxedfunc = ifun.metadata.get('py.boxedfunc', None)
  if boxedfunc is not None:
    h_impl = closure.intern(boxedfunc)
    lines = [
        'def %s(rts, _0):' % entry
      , [ 'args = (rts.variable(_0, i).hnf() for i in xrange(len(_0.successors)))'
        , '_0.rewrite(%s(rts, *args))' % h_impl
        ]
      ]
    return lines

def compile_rawfunc(interp, ifun, closure, entry):
  '''
  Compiles code for a raw built-in function.  See README.md.  Corresponds to
  the "py.rawfunc" metadata.

  Like compile_boxedfunc but does not head-normalize the arguments.  The
  left-hand-side expression is simply passed to the implementation function.
  '''
  rawfunc = ifun.metadata.get('py.rawfunc', None)
  if rawfunc is not None:
    h_impl = closure.intern(rawfunc)
    lines = [
        'def %s(rts, _0):' % entry
      , ['rts.Node(%s(rts, _0), target=_0.target)' % h_impl]
      ]
    return lines

def compile_unboxedfunc(interp, ifun, closure, entry):
  '''
  Compiles a function over primitive data.

  See README.md.  Corresponds to the "py.unboxedfunc" metadata.
  '''
  unboxedfunc = ifun.metadata.get('py.unboxedfunc', None)
  if unboxedfunc is not None:
    h_impl = closure.intern(unboxedfunc)
    h_eval = closure.intern(apply_unboxed)
    lines = [
        'def %s(rts, _0):' % entry
      , [ 'return %s(rts, %s, _0)' % (h_eval, h_impl) ]
      ]
    return lines
