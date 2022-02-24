'''
Code for synthesizing built-in functions and node info.
'''

from ..runtime.currylib.prelude.math import apply_unboxed
from six.moves import range
import operator as op

__all__ = ['synthesize_function']

def synthesize_function(*args, **kwds):
  '''
  Synthesize a special function, if possible, or return None.
  '''
  return synthesize_boxedfunc(*args, **kwds) or \
         synthesize_rawfunc(*args, **kwds) or \
         synthesize_unboxedfunc(*args, **kwds)

def synthesize_boxedfunc(interp, ifun, closure, entry):
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
      , [ 'args = (rts.variable(_0, i).hnf() for i in range(len(_0.successors)))'
        , '_0.rewrite(%s(rts, *args))' % h_impl
        ]
      ]
    return lines

def synthesize_rawfunc(interp, ifun, closure, entry):
  '''
  Compiles code for a raw built-in function.  See README.md.  Corresponds to
  the "py.rawfunc" metadata.

  Like synthesize_boxedfunc but does not head-normalize the arguments.  The
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

def synthesize_unboxedfunc(interp, ifun, closure, entry):
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

