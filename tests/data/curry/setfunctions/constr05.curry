{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
main = sortValues $ set1 (\u -> u =:= unknown) (y::Bool) where y free