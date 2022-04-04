from .backends.cxx.cyrtbindings import (
    Fingerprint, ChoiceState, LEFT, RIGHT, UNDETERMINED

  # Node flags.
  , F_INT_TYPE
  , F_CHAR_TYPE
  , F_FLOAT_TYPE
  , F_BOOL_TYPE
  , F_LIST_TYPE
  , F_TUPLE_TYPE
  , F_IO_TYPE
  , F_PARTIAL_TYPE
  , F_OPERATOR
  , F_MONADIC

  # Node tags.
  , T_UNBOXED
  , T_SETGRD
  , T_FAIL
  , T_CONSTR
  , T_FREE
  , T_FWD
  , T_CHOICE
  , T_FUNC
  , T_CTOR
  )

FLAGS = {
    F_INT_TYPE    : 'F_INT_TYPE'
  , F_CHAR_TYPE   : 'F_CHAR_TYPE'
  , F_FLOAT_TYPE  : 'F_FLOAT_TYPE'
  , F_BOOL_TYPE   : 'F_BOOL_TYPE'
  , F_LIST_TYPE   : 'F_LIST_TYPE'
  , F_TUPLE_TYPE  : 'F_TUPLE_TYPE'
  , F_IO_TYPE     : 'F_IO_TYPE'
  , F_PARTIAL_TYPE: 'F_PARTIAL_TYPE'
}
FLAGS.update({k:v for v,k in FLAGS.items()})

BITFLAGS = {
    F_OPERATOR: 'F_OPERATOR'
  , F_MONADIC : 'F_MONADIC'
  }
BITFLAGS.update({k:v for v,k in BITFLAGS.items()})
