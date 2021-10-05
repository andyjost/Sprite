{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
{-# ORACLE_RESULT * (_a, _a, _b) #-}
main :: (Bool, Bool, Bool)
main = chooseValue $ set2 f x y
    where f u v = (x, u, v)
          x,y free
