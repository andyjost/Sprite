'''
Builds a custom icurry.IModule holding the built-in parts of the Prelude.

This is merged into the real module compiled from Prelude.curry to resolve the
external declarations.
'''
from __future__ import absolute_import
from . import ModuleSpecification
from ....common import (
    T_FAIL, T_CONSTR, T_FREE, T_FWD, T_CHOICE, T_FUNC, T_CTOR
  , F_INT_TYPE, F_CHAR_TYPE, F_FLOAT_TYPE, F_BOOL_TYPE, F_LIST_TYPE, F_TUPLE_TYPE
  , F_IO_TYPE, F_PARTIAL_TYPE , F_OPERATOR, F_MONADIC
  )
from .... import icurry, inspect
import abc

# def _T(name, constructors):
#   return icurry.IDataType('Prelude.' + name, constructors, modulename='Prelude')
# def _C(name, *args, **kwds):
#   return icurry.IConstructor('Prelude.' + name, *args, modulename='Prelude', **kwds)
# def _F(name, *args, **kwds):
#   return icurry.IFunction('Prelude.' + name, *args, modulename='Prelude', **kwds)

# Types.
# ======
TYPES = [
    ('_Failure'   , [('_Failure'            , 0, {'all.tag'  : T_FAIL         })])
  , ('_Constraint', [('_StrictConstraint'   , 2, {'all.tag'  : T_CONSTR       })
                    ,('_NonStrictConstraint', 2, {'all.tag'  : T_CONSTR       })
                    ,('_ValueBinding'       , 2, {'all.tag'  : T_CONSTR       })])
  , ('_Free'      , [('_Free'               , 2, {'all.tag'  : T_FREE         })])
  , ('_Fwd'       , [('_Fwd'                , 1, {'all.tag'  : T_FWD          })])
  , ('_Choice'    , [('_Choice'             , 3, {'all.tag'  : T_CHOICE       })])
  , ('_PartApplic', [('_PartApplic'         , 2, {'all.flags': F_PARTIAL_TYPE })])
  , ('Bool'       , [('False'               , 0, {'all.flags': F_BOOL_TYPE    })
                    ,('True'                , 0, {'all.flags': F_BOOL_TYPE    })])
  , ('Char'       , [('Char'                , 1, {'all.flags': F_CHAR_TYPE    })])
  , ('Float'      , [('Float'               , 1, {'all.flags': F_FLOAT_TYPE   })])
  , ('Int'        , [('Int'                 , 1, {'all.flags': F_INT_TYPE     })])
  , ('IO'         , [('IO'                  , 1, {'all.flags': F_IO_TYPE      })])
  , ('(->)'       , [('->'                  , 2, {})])
  ]

# List
TYPES.append(
    ('[]', [
      (':' , 2, {'all.flags': F_LIST_TYPE })
    , ('[]', 0, {'all.flags': F_LIST_TYPE })
    ])
  )

# Tuples
MAX_TUPLE_SIZE = 15
Unit = ('()', [
    ('()', 0, {'all.flags': F_TUPLE_TYPE })
  ])
TYPES.append(Unit)
for i in range(2, MAX_TUPLE_SIZE):
  name = '(%s)' % (','*(i-1))
  Tuple = (name, [(name, i, {'all.flags': F_TUPLE_TYPE})])
  TYPES.append(Tuple)

# Functions.
# ==========
FUNCTIONS = [
      ('$##'                   , 2, {}                   )
    , ('$!'                    , 2, {}                   )
    , ('$!!'                   , 2, {}                   )
    , ('?'                     , 2, {}                   )
    , ('&'                     , 2, {}                   )
    , ('=:='                   , 2, {}                   )
    , ('=:<='                  , 2, {}                   )
    , ('apply'                 , 2, {}                   )
    , ('bindIO'                , 2, {'all.monadic': True})
    , ('catch'                 , 2, {'all.monadic': True})
    , ('cond'                  , 2, {}                   )
    , ('constrEq'              , 2, {}                   )
    , ('divInt'                , 2, {}                   )
    , ('ensureNotFree'         , 1, {}                   )
    , ('eqChar'                , 2, {}                   )
    , ('eqFloat'               , 2, {}                   )
    , ('eqInt'                 , 3, {}                   )
    , ('failed'                , 0, {}                   )
    , ('getChar'               , 0, {'all.monadic': True})
    , ('ltEqChar'              , 2, {}                   )
    , ('ltEqFloat'             , 2, {}                   )
    , ('ltEqInt'               , 2, {}                   )
    , ('minusInt'              , 2, {}                   )
    , ('modInt'                , 2, {}                   )
    , ('negateFloat'           , 1, {}                   )
    , ('nonstrictEq'           , 2, {}                   )
    , ('plusInt'               , 2, {}                   )
    , ('prim_acosFloat'        , 1, {}                   )
    , ('prim_acoshFloat'       , 1, {}                   )
    , ('prim_appendFile'       , 2, {'all.monadic': True})
    , ('prim_asinFloat'        , 1, {}                   )
    , ('prim_asinhFloat'       , 1, {}                   )
    , ('prim_atanFloat'        , 1, {}                   )
    , ('prim_atanhFloat'       , 1, {}                   )
    , ('prim_chr'              , 1, {}                   )
    , ('prim_constrEq'         , 2, {}                   )
    , ('prim_cosFloat'         , 1, {}                   )
    , ('prim_coshFloat'        , 1, {}                   )
    , ('prim_divFloat'         , 2, {}                   )
    , ('prim_error'            , 1, {}                   )
    , ('prim_expFloat'         , 1, {}                   )
    , ('prim_intToFloat'       , 1, {}                   )
    , ('prim_ioError'          , 1, {'all.monadic': True})
    , ('prim_logFloat'         , 1, {}                   )
    , ('prim_minusFloat'       , 2, {}                   )
    , ('prim_nonstrictEq'      , 2, {}                   )
    , ('prim_ord'              , 1, {}                   )
    , ('prim_plusFloat'        , 2, {}                   )
    , ('prim_putChar'          , 1, {'all.monadic': True})
    , ('prim_readCharLiteral'  , 1, {}                   )
    , ('prim_readFile'         , 1, {'all.monadic': True})
    , ('prim_readFloatLiteral' , 1, {}                   )
    , ('prim_readNatLiteral'   , 1, {}                   )
    , ('prim_readStringLiteral', 1, {}                   )
    , ('prim_roundFloat'       , 1, {}                   )
    , ('prim_showCharLiteral'  , 1, {}                   )
    , ('prim_showFloatLiteral' , 1, {}                   )
    , ('prim_showIntLiteral'   , 1, {}                   )
    , ('prim_showStringLiteral', 1, {}                   )
    , ('prim_sinFloat'         , 1, {}                   )
    , ('prim_sinhFloat'        , 1, {}                   )
    , ('prim_sqrtFloat'        , 1, {}                   )
    , ('prim_tanFloat'         , 1, {}                   )
    , ('prim_tanhFloat'        , 1, {}                   )
    , ('prim_timesFloat'       , 2, {}                   )
    , ('prim_truncateFloat'    , 1, {}                   )
    , ('prim_writeFile'        , 2, {'all.monadic': True})
    , ('_PyGenerator'          , 1, {}                   )
    , ('_PyString'             , 1, {}                   )
    , ('quotInt'               , 2, {}                   )
    , ('remInt'                , 2, {}                   )
    , ('returnIO'              , 1, {'all.monadic': True})
    , ('seqIO'                 , 2, {'all.monadic': True})
    , ('timesInt'              , 2, {}                   )
    # Unused PAKCS functions.
    , ('failure'               , 2, {}                   )
    , ('ifVar'                 , 2, {}                   )
    , ('letrec'                , 2, {}                   )
    , ('prim_divInt'           , 2, {}                   )
    , ('prim_eqChar'           , 2, {}                   )
    , ('prim_eqFloat'          , 2, {}                   )
    , ('prim_eqInt'            , 2, {}                   )
    , ('prim_ltEqChar'         , 2, {}                   )
    , ('prim_ltEqFloat'        , 2, {}                   )
    , ('prim_ltEqInt'          , 2, {}                   )
    , ('prim_minusInt'         , 2, {}                   )
    , ('prim_modInt'           , 3, {}                   )
    , ('prim_negateFloat'      , 1, {}                   )
    , ('prim_plusInt'          , 2, {}                   )
    , ('prim_quotInt'          , 2, {}                   )
    , ('prim_readFileContents' , 2, {}                   )
    , ('prim_remInt'           , 2, {}                   )
    , ('prim_timesInt'         , 2, {}                   )
    , ('unifEqLinear'          , 2, {}                   )
    ]

class PreludeSpecification(ModuleSpecification):
  # Note: derived classes should provide CONSTRUCTOR_METADATA and FUNCTION_METADATA.
  def types(self):
    for (typename, constructors) in TYPES:
      yield icurry.IDataType(
          'Prelude.' + typename
        , [ icurry.IConstructor(
                'Prelude.' + ctorname
              , arity
              , metadata=dict(md, **self.CONSTRUCTOR_METADATA.get((ctorname, i), {}))
              )
              for i,(ctorname, arity, md) in enumerate(constructors)
            ]
        , modulename='Prelude'
        )

  def functions(self):
    for name, arity, md in FUNCTIONS:
      yield icurry.IFunction(
          'Prelude.' + name
        , arity
        , modulename='Prelude'
        , metadata=dict(md, **self.FUNCTION_METADATA.get(name, {}))
        )

  def aliases(self):
    '''Returns prelude aliases.  Simply for convenience.'''
    yield 'Unit'  , '()'
    yield 'Pair'  , '(,)'
    yield 'Cons'  , ':'
    yield 'Nil'   , '[]'
    yield 'True_' , 'True'
    yield 'False_', 'False'

  def exports(self):
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
    for typename,_ in TYPES:
      if inspect.isa_tuple_name(typename):
        yield typename
    yield '(->)'
    # Helper functions.
    yield '_PyGenerator'
    yield '_PyString'
    # Clobber the definition of Prelude.? with Sprite's own.
    yield '?'
    # Include all of the primitives.  Sprite compiles the Prelude with __KICS2__
    # defined.  This hides some primitive functions.  To emulate PAKCS-style
    # fundamental types, we need those.
    for funcname,_, _ in FUNCTIONS:
      if funcname.startswith('prim_'):
        yield funcname

  def extern(self):
    return icurry.IModule(
          name='Prelude', imports=[]
        , types=self.types()
        , functions=self.functions()
        )

