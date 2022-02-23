'''
Code for synthesizing built-in functions and node info.
'''

from ....common import T_CTOR, T_FUNC
from .... import icurry, inspect
# from ..runtime.currylib.prelude.math import apply_unboxed
from six.moves import range
import operator as op

__all__ = [
    'synthesize_constructor_info'
  , 'synthesize_function'
  , 'synthesize_function_info_stub'
  ]

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
      , [ 'args = (rts.variable(_0, i).hnf() for i in range(len(_0.successors)))'
        , '_0.rewrite(%s(rts, *args))' % h_impl
        ]
      ]
    breakpoint()
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
    breakpoint()
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
    breakpoint()
    return lines

def synthesize_constructor_info(interp, itype, icons, extern):
  # For builtins, the 'all.tag' metadata contains the tag.
  builtin = 'all.tag' in icons.metadata
  metadata = icurry.metadata.getmd(icons, extern, itype=itype)
  InfoTable = interp.context.runtime.InfoTable
  pdbtrace()
  info = InfoTable(
      icons.name
    , icons.arity
    , T_CTOR + icons.index if not builtin else metadata['all.tag']
    , _nostep if not builtin else _unreachable
    , getattr(metadata, 'py.format', None)
    , _gettypechecker(interp, metadata)
    , getattr(metadata, 'all.flags', 0)
    )
  return info

def synthesize_function_info_stub(interp, ifun, extern):
  metadata = icurry.metadata.getmd(ifun, extern)
  InfoTable = interp.context.runtime.InfoTable
  breakpoint()
  info = InfoTable(
      ifun.name
    , ifun.arity
    , T_FUNC
    , None
    , getattr(metadata, 'py.format', None)
    , _gettypechecker(interp, metadata)
    , InfoTable.MONADIC if metadata.get('all.monadic') else 0
    )
  return info

def _nostep(*args, **kwds):
  pass

def _unreachable(*args, **kwds):
  assert False

# FIXME: several things in the info table now have an interpreter bound.  It
# would be great to simplify that.  Maybe it should just be added as an entry
# to the info table.
def _gettypechecker(interp, metadata):
  '''
  If debugging is enabled, and a typechecker is defined, get it and bind the
  interpreter.
  '''
  if interp.flags['debug']:
    checker = getattr(metadata, 'py.typecheck', None)
    if checker is not None:
      return lambda *args: checker(interp, *args)

