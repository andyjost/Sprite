'''
Builds a custom icurry.IModule holding the built-in parts of the Prelude.

This is merged into the real module compiled from Prelude.curry to resolve the
external declarations.
'''

from ....common import T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
from .graph import infotable
from .... import icurry, inspect
from . import prelude_impl as impl, typecheckers as tc
import math
import operator as op

def exports():
  '''
  Returns the name of each symbol that must be added to the Prelude but does
  not appear with a definition in Prelude.curry.
  '''
  # Special symbols.
  yield '_Failure'
  yield '_Constraint'
  yield '_Free'
  yield '_Fwd'
  yield '_Choice'
  yield '_PartApplic'
  # Opaque types.
  yield '[]'
  yield 'IO'
  for ty in _types_:
    name = ty.name
    if inspect.isa_tuple_name(name):
      yield name
  yield '(->)'
  # Helper functions.
  yield '_PyGenerator'
  # Clobber the definition of Prelude.? with Sprite's own.
  yield '?'
  # Include all of the primitives.  Sprite compiles the Prelude with __KICS2__
  # defined.  This hides some primitive functions.  To emulate PAKCS-style
  # fundamental types, we need those.
  for fun in _functions_:
    if fun.name.startswith('prim_'):
      yield fun.name

def aliases():
  '''Returns prelude aliases.  Simply for convenience.'''
  yield 'Unit', '()'
  yield 'Pair', '(,)'
  yield 'Cons', ':'
  yield 'Nil', '[]'


# Types.
# ======
def _T(name, constructors):
  return icurry.IDataType('Prelude.' + name, constructors)
def _C(name, *args, **kwds):
  return icurry.IConstructor('Prelude.' + name, *args, **kwds)

_types_ = [
    _T('_Failure'   , [_C('_Failure', 0, metadata={'py.format':'failure', 'all.tag':T_FAIL})])
  , _T('_Constraint'   , [
        _C('_StrictConstraint'   , 2
            , metadata={'all.tag':T_CONSTR, 'py.typecheck':tc.Constraint})
      , _C('_NonStrictConstraint', 2
            , metadata={'all.tag':T_CONSTR, 'py.typecheck':tc.Constraint})
      , _C('_ValueBinding', 2
            , metadata={'all.tag':T_CONSTR, 'py.typecheck':tc.Constraint})
      ])
    # Free variables have two successors, one for the variable ID (Int) and one
    # for the generator.  The second slot is initially set to Prelude.().  On
    # instantiation, it is replaced with a generator.
  , _T('_Free'      , [_C('_Free', 2, metadata={'py.format':'_{1}', 'all.tag':T_FREE})])
  , _T('_Fwd'       , [_C('_Fwd', 1, metadata={'py.format':'{1}', 'all.tag':T_FWD})])
  , _T('_Choice'    , [_C('_Choice', 3, metadata={'all.tag':T_CHOICE})])
  , _T('_PartApplic', [_C('_PartApplic', 2, metadata={'py.format': '{2}', 'all.tag':T_CTOR})])

  , _T('Bool'       , [ _C('False', 0, metadata={'all.flags': infotable.InfoTable.BOOL_TYPE})
                      , _C('True', 0, metadata={'all.flags': infotable.InfoTable.BOOL_TYPE})
                      ])
  , _T('Char'       , [_C('Char', 1, metadata={ 'py.format': '{1}', 'py.typecheck': tc.Char
                                              , 'all.flags': infotable.InfoTable.CHAR_TYPE
                                              })
                      ])
  , _T('Float'      , [_C('Float', 1, metadata={ 'py.format': '{1}', 'py.typecheck': tc.Float
                                               , 'all.flags': infotable.InfoTable.FLOAT_TYPE
                                               })
                      ])
  , _T('Int'        , [_C('Int', 1, metadata={ 'py.format': '{1}', 'py.typecheck': tc.Int
                                             , 'all.flags': infotable.InfoTable.INT_TYPE
                                             })
                      ])
  , _T('IO'         , [_C('IO', 1, metadata={'all.flags': infotable.InfoTable.IO_TYPE})])
  , _T('(->)'       , [_C('->', 2)])
  ]

# List
_types_.append(
    _T('[]', [
        _C(':' , 2, metadata={ 'py.format':'({1}:{2})'
                             , 'all.flags': infotable.InfoTable.LIST_TYPE
                             })
      , _C('[]', 0, metadata={ 'py.format':'[]'
                             , 'all.flags': infotable.InfoTable.LIST_TYPE
                             })
      ])
  )

# Tuples
MAX_TUPLE_SIZE = 15
Unit = _T('()', [
    _C('()', 0, metadata={ 'py.format':'()'
                         , 'all.flags': infotable.InfoTable.TUPLE_TYPE
                         })
  ])
_types_.append(Unit)
for i in range(2, MAX_TUPLE_SIZE):
  name = '(%s)' % (','*(i-1))
  Tuple = _T(name, [
      _C(
          name
        , i
        , metadata={
              'py.format':
                  '(%s)' % ', '.join(['{%d}' % j for j in range(1,i+1)])
            , 'all.flags': infotable.InfoTable.TUPLE_TYPE
            }
        )
    ])
  _types_.append(Tuple)

def _divMod_impl(x, y):
  # divMod_ x y = (x `div` y, x `mod` y)
  d = op.floordiv(x, y)
  m = x - y * d
  return d, m

def _quotRem_impl(x, y):
  # quotRem_ x y = (x `quot` y, x `rem` y)
  q = int(op.truediv(x, y))
  r = x - y * q
  return q, r

# Functions.
# ==========
def _F(name, *args, **kwds):
  return icurry.IFunction('Prelude.' + name, *args, **kwds)

_functions_ = [
    _F('_PyGenerator', 1
        , metadata={'py.boxedfunc':impl._PyGenerator}
        )
  # The following functions are for PAKCS-style integers.
  # The PAKCS-style Prelude reverses the argument order for binary operations.
  , _F('prim_plusInt'    , 2, metadata={'py.unboxedfunc': op.add})
  , _F('prim_minusInt'   , 2, metadata={'py.unboxedfunc': op.sub})
  , _F('prim_timesInt'   , 2, metadata={'py.unboxedfunc': op.mul})
  , _F('prim_divInt'     , 2, metadata={'py.unboxedfunc': op.floordiv})
  , _F('prim_eqInt'      , 2, metadata={'py.unboxedfunc': op.eq})
  , _F('prim_ltEqInt'    , 2, metadata={'py.unboxedfunc': op.le})
  , _F('prim_modInt'     , 2, metadata={'py.unboxedfunc': lambda x, y: x - y * op.floordiv(x,y)})
  , _F('prim_quotInt'    , 2, metadata={'py.unboxedfunc': lambda x, y: int(op.truediv(x, y))})
  , _F('prim_remInt'     , 2, metadata={'py.unboxedfunc': lambda x, y: x - y * int(op.truediv(x, y))})
  , _F('prim_eqChar'     , 2, metadata={'py.unboxedfunc': op.eq})
  , _F('prim_ltEqChar'   , 2, metadata={'py.unboxedfunc': op.le})
  , _F('prim_eqFloat'    , 2, metadata={'py.unboxedfunc': op.eq})
  , _F('prim_ltEqFloat'  , 2, metadata={'py.unboxedfunc': op.le})
  , _F('prim_negateFloat', 1, metadata={'py.unboxedfunc': op.neg})
  # The following functions are for KICS2-style integers.
  , _F('plusInt'    , 2, metadata={'py.rawfunc': impl.plusInt})
  , _F('minusInt'   , 2, metadata={'py.rawfunc': impl.minusInt})
  , _F('timesInt'   , 2, metadata={'py.rawfunc': impl.timesInt})
  , _F('divInt'     , 2, metadata={'py.rawfunc': impl.divInt})
  , _F('eqInt'      , 3, metadata={'py.rawfunc': impl.eqInt})
  , _F('ltEqInt'    , 2, metadata={'py.rawfunc': impl.ltEqInt})
  , _F('modInt'     , 2, metadata={'py.rawfunc': impl.modInt})
  , _F('quotInt'    , 2, metadata={'py.rawfunc': impl.quotInt})
  , _F('remInt'     , 2, metadata={'py.rawfunc': impl.remInt})
  , _F('eqChar'     , 2, metadata={'py.unboxedfunc': op.eq})
  , _F('ltEqChar'   , 2, metadata={'py.unboxedfunc': op.le})
  , _F('eqFloat'    , 2, metadata={'py.unboxedfunc': op.eq})
  , _F('ltEqFloat'  , 2, metadata={'py.unboxedfunc': op.le})
  , _F('negateFloat', 1, metadata={'py.unboxedfunc': op.neg})
  # (end)
  , _F('prim_plusFloat', 2, metadata={'py.unboxedfunc':op.add})
  , _F('prim_minusFloat', 2, metadata={'py.unboxedfunc':op.sub})
  , _F('prim_timesFloat', 2, metadata={'py.unboxedfunc':op.mul})
  , _F('prim_divFloat', 2, metadata={'py.unboxedfunc':op.truediv})
  , _F('prim_intToFloat', 1, metadata={'py.unboxedfunc':float})
  , _F('prim_truncateFloat', 1, metadata={'py.unboxedfunc':int})
  , _F('prim_roundFloat', 1, metadata={'py.unboxedfunc':lambda x: int(round(x))})
  , _F('prim_logFloat', 1, metadata={'py.unboxedfunc':math.log})
  , _F('prim_expFloat', 1, metadata={'py.unboxedfunc':math.exp})
  , _F('prim_sqrtFloat', 1, metadata={'py.unboxedfunc':math.sqrt})
  , _F('prim_sinFloat', 1, metadata={'py.unboxedfunc':math.sin})
  , _F('prim_cosFloat', 1, metadata={'py.unboxedfunc':math.cos})
  , _F('prim_tanFloat', 1, metadata={'py.unboxedfunc':math.tan})
  , _F('prim_asinFloat', 1, metadata={'py.unboxedfunc':math.asin})
  , _F('prim_acosFloat', 1, metadata={'py.unboxedfunc':math.acos})
  , _F('prim_atanFloat', 1, metadata={'py.unboxedfunc':math.atan})
  , _F('prim_sinhFloat', 1, metadata={'py.unboxedfunc':math.sinh})
  , _F('prim_coshFloat', 1, metadata={'py.unboxedfunc':math.cosh})
  , _F('prim_tanhFloat', 1, metadata={'py.unboxedfunc':math.tanh})
  , _F('prim_asinhFloat', 1, metadata={'py.unboxedfunc':math.asinh})
  , _F('prim_acoshFloat', 1, metadata={'py.unboxedfunc':math.acosh})
  , _F('prim_atanhFloat', 1, metadata={'py.unboxedfunc':math.atanh})
  , _F('ensureNotFree', 1, metadata={'py.rawfunc':impl.ensureNotFree})
  , _F('$!', 2, metadata={'py.rawfunc':impl.apply_hnf})
  , _F('$!!', 2, metadata={'py.rawfunc':impl.apply_nf})
  , _F('$##', 2, metadata={'py.rawfunc':impl.apply_gnf})
  , _F('prim_error', 1, metadata={'py.boxedfunc':impl.error})
  , _F('failed', 0, metadata={'py.boxedfunc':impl.failed})
  , _F('=:=', 2, metadata={'py.rawfunc':impl.constr_eq})
  , _F('constrEq', 2, metadata={'py.rawfunc':impl.constr_eq})
  , _F('prim_constrEq', 2, metadata={'py.rawfunc':impl.constr_eq})
  , _F('=:<=', 2, metadata={'py.rawfunc':impl.nonstrict_eq})
  , _F('nonstrictEq', 2, metadata={'py.rawfunc':impl.nonstrict_eq})
  , _F('prim_nonstrictEq', 2, metadata={'py.rawfunc':impl.nonstrict_eq})
  , _F('&', 2, metadata={'py.rawfunc':impl.concurrent_and})
  , _F('prim_ord', 1, metadata={'py.unboxedfunc':ord})
  , _F('prim_chr', 1, metadata={'py.unboxedfunc':chr})
  , _F('prim_intToFloat', 1, metadata={'py.unboxedfunc':float})
  , _F('prim_readNatLiteral', 1, metadata={'py.boxedfunc':impl.readNatLiteral})
  , _F('prim_readFloatLiteral', 1, metadata={'py.boxedfunc':impl.readFloatLiteral})
  , _F('prim_readCharLiteral', 1, metadata={'py.boxedfunc':impl.readCharLiteral})
  , _F('prim_readStringLiteral', 1, metadata={'py.boxedfunc':impl.readStringLiteral})
  , _F('prim_showCharLiteral', 1, metadata={'py.boxedfunc':impl.show})
  , _F('prim_showStringLiteral', 1, metadata={'py.boxedfunc':impl.show})
  , _F('prim_showIntLiteral', 1, metadata={'py.boxedfunc':impl.show})
  , _F('prim_showFloatLiteral', 1, metadata={'py.boxedfunc':impl.show})
  # I/O functions.
  , _F('bindIO', 2, metadata={'py.rawfunc':impl.bindIO, 'all.monadic':True})
  , _F('seqIO', 2, metadata={'py.rawfunc':impl.seqIO, 'all.monadic':True})
  , _F('returnIO', 1, metadata={'py.rawfunc':impl.returnIO, 'all.monadic':True})
  , _F('prim_putChar', 1, metadata={'py.boxedfunc':impl.putChar, 'all.monadic':True})
  , _F('getChar', 0, metadata={'py.boxedfunc':impl.getChar, 'all.monadic':True})
  , _F('prim_readFile', 1, metadata={'py.boxedfunc':impl.readFile, 'all.monadic':True})
  , _F('prim_writeFile', 2, metadata={'py.rawfunc':impl.writeFile, 'all.monadic':True})
  , _F('prim_appendFile', 2, metadata={'py.rawfunc':impl.appendFile, 'all.monadic':True})
  , _F('catch', 2, metadata={'py.rawfunc':impl.catch, 'all.monadic':True})
  , _F('prim_ioError', 1, metadata={'py.rawfunc':impl.ioError, 'all.monadic':True})
  , _F('?', 2, metadata={'py.rawfunc':impl.choice})
  , _F('apply', 2, metadata={'py.rawfunc':impl.apply})
  , _F('cond', 2, metadata={'py.rawfunc':impl.cond})
  # Unused PAKCS functions.
  , _F('unifEqLinear', 2, metadata={'py.rawfunc': impl.not_used})
  , _F('prim_readFileContents', 2, metadata={'py.rawfunc': impl.not_used})
  , _F('ifVar', 2, metadata={'py.rawfunc': impl.not_used})
  , _F('letrec', 2, metadata={'py.rawfunc': impl.not_used})
  , _F('failure', 2, metadata={'py.rawfunc': impl.not_used})
  ]

Prelude = icurry.IModule(
    name='Prelude', imports=[], types=_types_, functions=_functions_
  )
