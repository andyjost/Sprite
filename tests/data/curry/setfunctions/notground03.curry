{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
main = sortValues $
  set1 (\u -> let x=unknown in u=:=x &> (z::Bool)) (y::Bool)
  where y,z free
