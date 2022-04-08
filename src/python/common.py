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
  , F_CSTRING_TYPE
  , F_MONADIC
  , F_OPERATOR
  , F_STATIC_OBJECT

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
  , F_CSTRING_TYPE: 'F_CSTRING_TYPE'
}
FLAGS.update({k:v for v,k in FLAGS.items()})

BITFLAGS = {
    F_MONADIC       : 'F_MONADIC'
  , F_OPERATOR      : 'F_OPERATOR'
  , F_STATIC_OBJECT : 'F_STATIC_OBJECT'
  }
BITFLAGS.update({k:v for v,k in BITFLAGS.items()})
