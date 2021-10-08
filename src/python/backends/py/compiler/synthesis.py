'''
Code for synthesizing built-in functions.
'''

import operator as op
from ..runtime.fairscheme import hnf_or_free  # Fixme: should be a method of variable
from ..runtime import graph
from .... import inspect

__all__ = ['synthesize_function']

def synthesize_function(interp, ifun):
  '''
  Synthesize a special function, if possible, or return None.
  '''
  return compile_boxedfunc(interp, ifun) or \
         compile_rawfunc(interp, ifun) or \
         compile_unboxedfunc(interp, ifun)

def compile_boxedfunc(interp, ifun):
  '''
  Compiles code for a built-in function.  See README.md.  Corresponds to the
  "py.boxedfunc" metadata.

  The Python implementation function must accept the arguments in head-normal
  form, but without any other preprocessing (e.g., unboxing).  It returns a
  sequence of arguments accepted by ``runtime.Node.__new__``.
  '''
  boxedfunc = ifun.metadata.get('py.boxedfunc', None)
  if boxedfunc is not None:
    def step(rts, _0):
      args = (rts.variable(_0, i).hnf() for i in xrange(len(_0.successors)))
      _0.rewrite(boxedfunc(rts, *args))
    return step


def compile_rawfunc(interp, ifun):
  '''
  Compiles code for a raw built-in function.  See README.md.  Corresponds to
  the "py.rawfunc" metadata.

  Like compile_boxedfunc but does not head-normalize the arguments.  The
  left-hand-side expression is simply passed to the implementation function.
  '''
  rawfunc = ifun.metadata.get('py.rawfunc', None)
  if rawfunc is not None:
    def step(rts, _0):
      graph.Node(rawfunc(rts, _0), target=_0.target)
    return step


def with_unboxed_args(f):
  '''
  Calls a wrapped function with unboxed args.  This will normalize the
  arguments, raising E_RESIDUAL when they are not ground.

  The decorated function should generate arguments to a node replaement.
  '''
  def repl(rts, _0):
    args = [
        hnf_or_free(rts, rts.variable(_0, i))
            for i in xrange(len(_0.successors))
      ]
    freevars = [arg for arg in args if inspect.isa_freevar(arg.target)]
    if freevars:
      rts.suspend(freevars)
    else:
      args = (arg.unboxed_value for arg in args)
      result = f(rts, *args)
      return graph.Node(*result, target=_0)
  return repl

HANDLERS = {
    bool:  lambda rts, rv: [getattr(rts.prelude, 'True' if rv else 'False')]
  , float: lambda rts, rv: [rts.prelude.Float, rv]
  , int:   lambda rts, rv: [rts.prelude.Int, rv]
  , str:   lambda rts, rv: [rts.prelude.Char, rv]
  }

def compile_unboxedfunc(interp, ifun):
  '''
  Compiles a function over primitive data.

  See README.md.  Corresponds to the "py.unboxedfunc" metadata.
  '''
  unboxedfunc = ifun.metadata.get('py.unboxedfunc', None)
  if unboxedfunc is not None:
    @with_unboxed_args
    def step(rts, *args):
      result_value = unboxedfunc(*args)
      handler = HANDLERS[type(result_value)]
      return handler(rts, result_value)
    return step
