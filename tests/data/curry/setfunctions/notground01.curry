{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
{-# ORACLE_RESULT * (_a, _a) #-}
main :: (Bool, Bool)
main = chooseValue $ set1 f x
    where f u = (x, u)
          x free
