{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
{-# ORACLE_RESULT * _a #-}
main :: Bool
main = chooseValue $ set0 f
    where f = x
          x free
