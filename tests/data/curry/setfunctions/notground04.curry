{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
{-# ORACLE_RESULT * [_a] #-}
main = sortValues $
  set1 (\u -> let x=unknown in u=:=x &> x) (y::Bool)
  where y free
