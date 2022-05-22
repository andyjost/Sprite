from ..graph import InfoTable
from ....common import *

__all__ = [
      'Choice', 'Failure', 'Free', 'Fwd', 'NonStrictConstraint'
    , 'PartApplic', 'SetGuard', 'StrictConstraint', 'ValueBinding'
    ]

Choice = InfoTable('_Choice', 3, T_CHOICE, 0, None, None)
Failure = InfoTable('_Failure', 0, T_FAIL, 0, None, 'failed')
Free = InfoTable('_Free', 2, T_FREE, 0, None, '_{1}')
Fwd = InfoTable('_Fwd', 1, T_FWD, 0, None, '{1}')
NonStrictConstraint = InfoTable('_NonStrictConstraint', 2, T_CONSTR, 0, None, None)
PartApplic = InfoTable('_PartApplic', 2, T_CTOR, F_PARTIAL_TYPE, None, '{2}')
SetGuard = InfoTable('_SetGuard', 2, -7, 0, None, None)
StrictConstraint = InfoTable('_StrictConstraint', 2, T_CONSTR, 0, None, None)
ValueBinding = InfoTable('_ValueBinding', 2, T_CONSTR, 0, None, None)
