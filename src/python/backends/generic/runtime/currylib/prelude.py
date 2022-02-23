'''
Builds a custom icurry.IModule holding the built-in parts of the Prelude.

This is merged into the real module compiled from Prelude.curry to resolve the
external declarations.
'''
from __future__ import absolute_import
from . import ModuleSpecification
from .....common import (
    T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
  , INT_TYPE, CHAR_TYPE, FLOAT_TYPE, BOOL_TYPE, LIST_TYPE, TUPLE_TYPE
  , IO_TYPE, PARTIAL_TYPE , OPERATOR, MONADIC
  )
from ..... import icurry, inspect

def _T(name, constructors):
  return icurry.IDataType('Prelude.' + name, constructors, modulename='Prelude')
def _C(name, *args, **kwds):
  return icurry.IConstructor('Prelude.' + name, *args, modulename='Prelude', **kwds)
def _F(name, *args, **kwds):
  return icurry.IFunction('Prelude.' + name, *args, modulename='Prelude', **kwds)
  
# Types.
# ======
TYPES = [
    _T('_Failure'   , [_C('_Failure'            , 0, metadata={'all.tag'  : T_FAIL       })])
  , _T('_Constraint', [_C('_StrictConstraint'   , 2, metadata={'all.tag'  : T_CONSTR     })
                      ,_C('_NonStrictConstraint', 2, metadata={'all.tag'  : T_CONSTR     })
                      ,_C('_ValueBinding'       , 2, metadata={'all.tag'  : T_CONSTR     })])
  , _T('_Free'      , [_C('_Free'               , 2, metadata={'all.tag'  : T_FREE       })])
  , _T('_Fwd'       , [_C('_Fwd'                , 1, metadata={'all.tag'  : T_FWD        })])
  , _T('_Choice'    , [_C('_Choice'             , 3, metadata={'all.tag'  : T_CHOICE     })])
  , _T('_PartApplic', [_C('_PartApplic'         , 2, metadata={'all.flags': PARTIAL_TYPE })])
  , _T('Bool'       , [_C('False'               , 0, metadata={'all.flags': BOOL_TYPE    })
                      ,_C('True'                , 0, metadata={'all.flags': BOOL_TYPE    })])
  , _T('Char'       , [_C('Char'                , 1, metadata={'all.flags': CHAR_TYPE    })])
  , _T('Float'      , [_C('Float'               , 1, metadata={'all.flags': FLOAT_TYPE   })])
  , _T('Int'        , [_C('Int'                 , 1, metadata={'all.flags': INT_TYPE     })])
  , _T('IO'         , [_C('IO'                  , 1, metadata={'all.flags': IO_TYPE      })])
  , _T('(->)'       , [_C('->'                  , 2)])
  ]

# List
TYPES.append(
    _T('[]', [
        _C(':' , 2, metadata={'all.flags': LIST_TYPE })
      , _C('[]', 0, metadata={'all.flags': LIST_TYPE })
      ])
  )

# Tuples
MAX_TUPLE_SIZE = 15
Unit = _T('()', [
    _C('()', 0, metadata={'all.flags': TUPLE_TYPE })
  ])
TYPES.append(Unit)
for i in range(2, MAX_TUPLE_SIZE):
  name = '(%s)' % (','*(i-1))
  Tuple = _T(name, [_C(name, i, metadata={'all.flags': TUPLE_TYPE})])
  TYPES.append(Tuple)

# Functions.
# ==========
FUNCTIONS = [
      _F('$##'                   , 2                                )
    , _F('$!'                    , 2                                )
    , _F('$!!'                   , 2                                )
    , _F('?'                     , 2                                )
    , _F('&'                     , 2                                )
    , _F('=:='                   , 2                                )
    , _F('=:<='                  , 2                                )
    , _F('apply'                 , 2                                )
    , _F('bindIO'                , 2, metadata={'all.monadic': True})
    , _F('catch'                 , 2, metadata={'all.monadic': True})
    , _F('cond'                  , 2                                )
    , _F('constrEq'              , 2                                )
    , _F('divInt'                , 2                                )
    , _F('ensureNotFree'         , 1                                )
    , _F('eqChar'                , 2                                )
    , _F('eqFloat'               , 2                                )
    , _F('eqInt'                 , 3                                )
    , _F('failed'                , 0                                )
    , _F('getChar'               , 0, metadata={'all.monadic': True})
    , _F('ltEqChar'              , 2                                )
    , _F('ltEqFloat'             , 2                                )
    , _F('ltEqInt'               , 2                                )
    , _F('minusInt'              , 2                                )
    , _F('modInt'                , 2                                )
    , _F('negateFloat'           , 1                                )
    , _F('nonstrictEq'           , 2                                )
    , _F('plusInt'               , 2                                )
    , _F('prim_acosFloat'        , 1                                )
    , _F('prim_acoshFloat'       , 1                                )
    , _F('prim_appendFile'       , 2, metadata={'all.monadic': True})
    , _F('prim_asinFloat'        , 1                                )
    , _F('prim_asinhFloat'       , 1                                )
    , _F('prim_atanFloat'        , 1                                )
    , _F('prim_atanhFloat'       , 1                                )
    , _F('prim_chr'              , 1                                )
    , _F('prim_constrEq'         , 2                                )
    , _F('prim_cosFloat'         , 1                                )
    , _F('prim_coshFloat'        , 1                                )
    , _F('prim_divFloat'         , 2                                )
    , _F('prim_error'            , 1                                )
    , _F('prim_expFloat'         , 1                                )
    , _F('prim_intToFloat'       , 1                                )
    , _F('prim_ioError'          , 1, metadata={'all.monadic': True})
    , _F('prim_logFloat'         , 1                                )
    , _F('prim_minusFloat'       , 2                                )
    , _F('prim_nonstrictEq'      , 2                                )
    , _F('prim_ord'              , 1                                )
    , _F('prim_plusFloat'        , 2                                )
    , _F('prim_putChar'          , 1, metadata={'all.monadic': True})
    , _F('prim_readCharLiteral'  , 1                                )
    , _F('prim_readFile'         , 1, metadata={'all.monadic': True})
    , _F('prim_readFloatLiteral' , 1                                )
    , _F('prim_readNatLiteral'   , 1                                )
    , _F('prim_readStringLiteral', 1                                )
    , _F('prim_roundFloat'       , 1                                )
    , _F('prim_showCharLiteral'  , 1                                )
    , _F('prim_showFloatLiteral' , 1                                )
    , _F('prim_showIntLiteral'   , 1                                )
    , _F('prim_showStringLiteral', 1                                )
    , _F('prim_sinFloat'         , 1                                )
    , _F('prim_sinhFloat'        , 1                                )
    , _F('prim_sqrtFloat'        , 1                                )
    , _F('prim_tanFloat'         , 1                                )
    , _F('prim_tanhFloat'        , 1                                )
    , _F('prim_timesFloat'       , 2                                )
    , _F('prim_truncateFloat'    , 1                                )
    , _F('prim_writeFile'        , 2, metadata={'all.monadic': True})
    , _F('_PyGenerator'          , 1                                )
    , _F('_PyString'             , 1                                )
    , _F('quotInt'               , 2                                )
    , _F('remInt'                , 2                                )
    , _F('returnIO'              , 1, metadata={'all.monadic': True})
    , _F('seqIO'                 , 2, metadata={'all.monadic': True})
    , _F('timesInt'              , 2                                )
    # Unused PAKCS functions.
    , _F('failure'               , 2                                )
    , _F('ifVar'                 , 2                                )
    , _F('letrec'                , 2                                )
    , _F('prim_divInt'           , 2                                )
    , _F('prim_eqChar'           , 2                                )
    , _F('prim_eqFloat'          , 2                                )
    , _F('prim_eqInt'            , 2                                )
    , _F('prim_ltEqChar'         , 2                                )
    , _F('prim_ltEqFloat'        , 2                                )
    , _F('prim_ltEqInt'          , 2                                )
    , _F('prim_minusInt'         , 2                                )
    , _F('prim_modInt'           , 3                                )
    , _F('prim_negateFloat'      , 1                                )
    , _F('prim_plusInt'          , 2                                )
    , _F('prim_quotInt'          , 2                                )
    , _F('prim_readFileContents' , 2                                )
    , _F('prim_remInt'           , 2                                )
    , _F('prim_timesInt'         , 2                                )
    , _F('unifEqLinear'          , 2                                )
    ]

MODULE = icurry.IModule(
      name='Prelude', imports=[], types=TYPES, functions=FUNCTIONS
    )

class PreludeSpecification(ModuleSpecification):
  @staticmethod
  def aliases():
    '''Returns prelude aliases.  Simply for convenience.'''
    yield 'Unit'  , '()'
    yield 'Pair'  , '(,)'
    yield 'Cons'  , ':'
    yield 'Nil'   , '[]'
    yield 'True_' , 'True'
    yield 'False_', 'False'
  
  @staticmethod
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
    for ty in TYPES:
      name = ty.name
      if inspect.isa_tuple_name(name):
        yield name
    yield '(->)'
    # Helper functions.
    yield '_PyGenerator'
    yield '_PyString'
    # Clobber the definition of Prelude.? with Sprite's own.
    yield '?'
    # Include all of the primitives.  Sprite compiles the Prelude with __KICS2__
    # defined.  This hides some primitive functions.  To emulate PAKCS-style
    # fundamental types, we need those.
    for fun in FUNCTIONS:
      if fun.name.startswith('prim_'):
        yield fun.name
  
  @staticmethod
  def extern():
    return MODULE
  
