__all__ = [
    'T_SETGRD', 'T_FAIL', 'T_CONSTR', 'T_VAR', 'T_FWD', 'T_CHOICE', 'T_FUNC'
  , 'T_CTOR'
  , 'ChoiceState', 'LEFT', 'RIGHT', 'UNDETERMINED'
  ]

T_SETGRD = -7
T_FAIL   = -6
T_CONSTR = -5
T_VAR    = -4
T_FWD    = -3
T_CHOICE = -2
T_FUNC   = -1
T_CTOR   =  0 # for each type, ctors are numbered starting at zero.

from .backends.py.sprite import ChoiceState, LEFT, RIGHT, UNDETERMINED

