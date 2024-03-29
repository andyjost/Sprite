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
from .... import inspect
import abc

# Types.
# ======
TYPES = [
    ('Bool'       , [('False'               , 0, {'all.flags': F_BOOL_TYPE    })
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
      ('$##'                   , 2, {}                      )
    , ('$!'                    , 2, {}                      )
    , ('$!!'                   , 2, {}                      )
    , ('?'                     , 2, {}                      )
    , ('&'                     , 2, {}                      )
    , ('apply'                 , 2, {}                      )
    , ('bindIO'                , 2, {'all.flags': F_MONADIC})
    , ('catch'                 , 2, {'all.flags': F_MONADIC})
    , ('cond'                  , 2, {}                      )
    , ('constrEq'              , 2, {}                      )
    , ('divInt'                , 2, {}                      )
    , ('ensureNotFree'         , 1, {}                      )
    , ('eqChar'                , 2, {}                      )
    , ('eqFloat'               , 2, {}                      )
    , ('eqInt'                 , 3, {}                      )
    , ('failed'                , 0, {}                      )
    , ('getChar'               , 0, {'all.flags': F_MONADIC})
    , ('ltEqChar'              , 2, {}                      )
    , ('ltEqFloat'             , 2, {}                      )
    , ('ltEqInt'               , 2, {}                      )
    , ('minusInt'              , 2, {}                      )
    , ('modInt'                , 2, {}                      )
    , ('negateFloat'           , 1, {}                      )
    , ('nonstrictEq'           , 2, {}                      )
    , ('plusInt'               , 2, {}                      )
    , ('prim_acosFloat'        , 1, {}                      )
    , ('prim_acoshFloat'       , 1, {}                      )
    , ('prim_appendFile'       , 2, {'all.flags': F_MONADIC})
    , ('prim_asinFloat'        , 1, {}                      )
    , ('prim_asinhFloat'       , 1, {}                      )
    , ('prim_atanFloat'        , 1, {}                      )
    , ('prim_atanhFloat'       , 1, {}                      )
    , ('prim_chr'              , 1, {}                      )
    , ('prim_cosFloat'         , 1, {}                      )
    , ('prim_coshFloat'        , 1, {}                      )
    , ('prim_divFloat'         , 2, {}                      )
    , ('prim_error'            , 1, {}                      )
    , ('prim_expFloat'         , 1, {}                      )
    , ('prim_intToFloat'       , 1, {}                      )
    , ('prim_ioError'          , 1, {'all.flags': F_MONADIC})
    , ('prim_logFloat'         , 1, {}                      )
    , ('prim_minusFloat'       , 2, {}                      )
    , ('prim_ord'              , 1, {}                      )
    , ('prim_plusFloat'        , 2, {}                      )
    , ('prim_putChar'          , 1, {'all.flags': F_MONADIC})
    , ('prim_readCharLiteral'  , 1, {}                      )
    , ('prim_readFile'         , 1, {'all.flags': F_MONADIC})
    , ('prim_readFloatLiteral' , 1, {}                      )
    , ('prim_readNatLiteral'   , 1, {}                      )
    , ('prim_readStringLiteral', 1, {}                      )
    , ('prim_roundFloat'       , 1, {}                      )
    , ('prim_showCharLiteral'  , 1, {}                      )
    , ('prim_showFloatLiteral' , 1, {}                      )
    , ('prim_showIntLiteral'   , 1, {}                      )
    , ('prim_showStringLiteral', 1, {}                      )
    , ('prim_sinFloat'         , 1, {}                      )
    , ('prim_sinhFloat'        , 1, {}                      )
    , ('prim_sqrtFloat'        , 1, {}                      )
    , ('prim_tanFloat'         , 1, {}                      )
    , ('prim_tanhFloat'        , 1, {}                      )
    , ('prim_timesFloat'       , 2, {}                      )
    , ('prim_truncateFloat'    , 1, {}                      )
    , ('prim_writeFile'        , 2, {'all.flags': F_MONADIC})
    , ('quotInt'               , 2, {}                      )
    , ('remInt'                , 2, {}                      )
    , ('returnIO'              , 1, {'all.flags': F_MONADIC})
    , ('seqIO'                 , 2, {'all.flags': F_MONADIC})
    , ('timesInt'              , 2, {}                      )
    # Unused PAKCS functions.
    , ('failure'               , 2, {}                      )
    , ('ifVar'                 , 2, {}                      )
    , ('letrec'                , 2, {}                      )
    , ('prim_readFileContents' , 2, {}                      )
    , ('unifEqLinear'          , 2, {}                      )
    # Internal use.
    , ('_biGenerator'          , 1, {}                      )
    , ('_biString'             , 1, {}                      )
    ]

class PreludeSpecification(ModuleSpecification):
  # Note: derived classes should provide CONSTRUCTOR_METADATA,
  # FUNCTION_METADATA, and TYPE_METADATA.
  NAME      = 'Prelude'
  TYPES     = TYPES
  FUNCTIONS = FUNCTIONS
  IMPORTS   = []

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
    Returns the name of each symbol that must be copied to the Prelude.  This
    is allowed to clobber symbols defined in Prelude.curry.
    '''
    # Opaque types.
    yield '[]'
    yield 'IO'
    for typename,_ in self.TYPES:
      if inspect.isa_tuple_name(typename):
        yield typename
    yield '(->)'
    yield '_biGenerator'
    # Include all of the primitives.  Sprite compiles the Prelude with __KICS2__
    # defined.  This hides some primitive functions.  To emulate PAKCS-style
    # fundamental types, we need those.
    for funcname,_, _ in self.FUNCTIONS:
      if funcname.startswith('prim_'):
        yield funcname


