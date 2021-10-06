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


# TODO: I don't think the typename is actually needed here.
def with_unboxed_args(typename):
  '''
  Calls a wrapped function with unboxed args.  This will normalize the
  arguments, raising E_RESIDUAL when they are not ground.

  The decorated function should generate arguments to a node replaement.
  '''
  assert typename in ['Int', 'Char', 'Float']
  def decorator(f):
    def repl(rts, _0):
      typedef = getattr(rts.prelude, typename).info.typedef()
      args = [
          hnf_or_free(rts, rts.variable(_0, i), typedef=typedef)
              for i in xrange(len(_0.successors))
        ]
      variables = [arg for arg in args if inspect.isa_freevar(arg.target)]
      if variables:
        rts.suspend(variables)
      else:
        args = (arg.unboxed_value for arg in args)
        result = f(rts, *args)
        return graph.Node(*result, target=_0)
    return repl
  return decorator

def compile_unboxedfunc(interp, ifun):
  '''
  Compiles a function over primitive data.

  See README.md.  Corresponds to the "py.unboxedfunc" metadata.
  '''
  md = ifun.metadata.get('py.unboxedfunc', None)
  if md is not None:
    # The metadata is either a function or a triple of (function, typename,
    # rtypename).
    if isinstance(md, tuple):
      unboxedfunc, typename, rtypename = md
    else:
      unboxedfunc = md
      typename, = (ty for ty in ['Int', 'Char', 'Float'] if ty in ifun.name)
      if any(ifun.name.startswith(stem) for stem in ['eq', 'lt', 'prim_eq', 'prim_lt']):
        rtypename = 'Bool'
      else:
        rtypename = typename
    if rtypename == 'Bool':
      # The result type is Boolean.  E.g., eqInt.
      @with_unboxed_args(typename)
      def step(rts, lhs, rhs):
        result_value = unboxedfunc(lhs, rhs)
        yield rts.prelude.True if result_value else rts.prelude.False
    else:
      # The result type matches the argument type.  E.g., plusInt
      @with_unboxed_args(typename)
      def step(rts, *args):
        typeinfo = getattr(rts.prelude, typename)
        result_value = unboxedfunc(*args)
        yield typeinfo
        yield result_value
    return step
