{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
main = (x, sortValues $ set1 (\u -> u =:= x) a, x) where x free