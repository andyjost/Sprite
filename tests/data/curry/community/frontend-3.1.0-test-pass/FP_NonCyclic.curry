{-# Language FunctionalPatterns #-}
last (_++[x]) = x

f1 = 42
f2 e            = [e]
f  = let f3 (FP_NonCyclic.f1) = 0
         f4 (f2 _)       = 23
      in f1
