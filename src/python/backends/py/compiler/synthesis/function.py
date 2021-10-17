'''
Code for synthesizing built-in functions.
'''

from ..... import inspect
from .. import ir, statics
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

def with_unboxed_args(f):
  '''
  Calls a wrapped function with unboxed args.  This will normalize the
  arguments, raising E_RESIDUAL when they are not ground.

  The decorated function should generate arguments to a node replaement.
  '''
  def repl(rts, _0):
    args = [
        rts.variable(_0, i).hnf_or_free()
            for i in xrange(len(_0.successors))
      ]
    freevars = [arg for arg in args if inspect.isa_freevar(arg.target)]
    if freevars:
      rts.suspend(freevars)
    else:
      args = (arg.unboxed_value for arg in args)
      result = f(rts, *args)
      return rts.Node(*result, target=_0)
  return repl

HANDLERS = {
    bool:  lambda rts, rv: [getattr(rts.prelude, 'True' if rv else 'False')]
  , float: lambda rts, rv: [rts.prelude.Float, rv]
  , int:   lambda rts, rv: [rts.prelude.Int, rv]
  , str:   lambda rts, rv: [rts.prelude.Char, rv]
  }

def get_handler(key):
  return HANDLERS[key]

def compile_unboxedfunc(interp, ifun, closure, entry):
  '''
  Compiles a function over primitive data.

  See README.md.  Corresponds to the "py.unboxedfunc" metadata.
  '''
  unboxedfunc = ifun.metadata.get('py.unboxedfunc', None)
  if unboxedfunc is not None:
    h_decorator = closure.intern(with_unboxed_args)
    h_gethandler = closure.intern(get_handler)
    h_impl = closure.intern(unboxedfunc)
    lines = [
        '@%s' % h_decorator
      , 'def %s(rts, *args):' % entry
      , [ 'result_value = %s(*args)' % h_impl
        , 'handler = %s(type(result_value))' % h_gethandler
        , 'return handler(rts, result_value)'
        ]
      ]
    return lines
