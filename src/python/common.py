__all__ = [
    'T_SETGRD', 'T_FAIL', 'T_CONSTR', 'T_FREE', 'T_FWD', 'T_CHOICE', 'T_FUNC'
  , 'T_CTOR'
  , 'ChoiceState', 'LEFT', 'RIGHT', 'UNDETERMINED'
  , 'INT_TYPE', 'CHAR_TYPE', 'FLOAT_TYPE', 'BOOL_TYPE', 'LIST_TYPE'
  , 'TUPLE_TYPE', 'IO_TYPE', 'PARTIAL_TYPE', 'OPERATOR', 'MONADIC'
  ]

# Node class tags.
T_SETGRD = -7
T_FAIL   = -6
T_CONSTR = -5
T_FREE   = -4
T_FWD    = -3
T_CHOICE = -2
T_FUNC   = -1
T_CTOR   =  0 # constructors for each Curry type are numbered from zero.

from ._sprite import (
    Fingerprint, ChoiceState, LEFT, RIGHT, UNDETERMINED
  , INT_TYPE, CHAR_TYPE, FLOAT_TYPE, BOOL_TYPE, LIST_TYPE
  , TUPLE_TYPE, IO_TYPE, PARTIAL_TYPE, OPERATOR, MONADIC
  )

# # InfoTable flags.
# # Constructor flags.
# INT_TYPE       = 0x1 # Prelude.Int
# CHAR_TYPE      = 0x2 # Prelude.Char
# FLOAT_TYPE     = 0x3 # Prelude.Float
# BOOL_TYPE      = 0x4 # Constructor of Prelude.Bool
# LIST_TYPE      = 0x5 # Constructor of Prelude.List
# TUPLE_TYPE     = 0x6 # Constructor of Prelude.() et. al
# IO_TYPE        = 0x7 # Constructor of Prelude.IO
# PARTIAL_TYPE   = 0x8 # A partial application
# OPERATOR       = 0x9 # Whether this is an operator.
# # Function flags.
# MONADIC = 0x10 # Whether any monadic function can be reached.

