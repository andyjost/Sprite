{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
{-# ORACLE_RESULT * Values [G_F, G_T, H_F, H_T] #-}
main = evalS (set f1' $< x) where x free
