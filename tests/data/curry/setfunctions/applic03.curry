{-# LANGUAGE CPP #-}
{-# ORACLE KICS2 #-}

#ifdef __KICS2__
import SetFunctions
#else
import Control.SetFunctions
#endif

import Common
{-# ORACLE_RESULT * Values [G_F] #-}
{-# ORACLE_RESULT * Values [G_T] #-}
{-# ORACLE_RESULT * Values [H_F] #-}
{-# ORACLE_RESULT * Values [H_T] #-}
main = evalS (set f1 $> x) where x free
