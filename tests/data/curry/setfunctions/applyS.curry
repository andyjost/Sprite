import Control.SetFunctions

-------------------------------------------
-- Examples with one argument.

data R = F_T | F_F | G_T | G_F deriving Show

f True  = F_T
f False = F_F
g True  = G_T
g False = G_F

h = f ? g
h' x = f x ? g x

-- Split on the argument.
goal0 = evalS (set f $> x) where x free
  {-# ORACLE_RESULT goal0: Values [F_F] #-}
  {-# ORACLE_RESULT goal0: Values [F_T] #-}

-- No splits.
goal1 = evalS (set f $< x) where x free
  {-# ORACLE_RESULT goal1: Values [F_F, F_T] #-}

-- Split on f/g.  (h) reduces to (f) and (g).
goal2 = evalS (set h $< x) where x free
  {-# ORACLE_RESULT goal2: Values [F_F, F_T] #-}
  {-# ORACLE_RESULT goal2: Values [G_F, G_T] #-}

-- Split on f/g and the argument.
goal3 = evalS (set h $> x) where x free
  {-# ORACLE_RESULT goal3: Values [F_F] #-}
  {-# ORACLE_RESULT goal3: Values [F_T] #-}
  {-# ORACLE_RESULT goal3: Values [G_F] #-}
  {-# ORACLE_RESULT goal3: Values [G_T] #-}

-- No splits.  (h') is not reducible.
goal4 = evalS (set h' $< x) where x free
  {-# ORACLE_RESULT goal4: Values [F_F, F_T, G_F, G_T] #-}

-- Split on the argument only.
goal5 = evalS (set h' $> x) where x free
  {-# ORACLE_RESULT goal5: Values [F_F, G_F] #-}
  {-# ORACLE_RESULT goal5: Values [F_T, G_T] #-}

-------------------------------------------
-- Tests for including or excluding non-determinism.

goal10 = evalS (set f $< x $> x)
    where x = True ? False
          f a b = (a, b)
  {-# ORACLE_RESULT goal10: Values [(True, True)] #-}
  {-# ORACLE_RESULT goal10: Values [(False, False)] #-}

goal11 = evalS (set f $> x $< x)
    where x = True ? False
          f a b = (a, b)
  {-# ORACLE_RESULT goal11: Values [(True, True)] #-}
  {-# ORACLE_RESULT goal11: Values [(False, False)] #-}

-- goal12 :: Values (Int, Int, Bool, Bool)
-- goal12 = evalS (set f $< (1,x) $> (x,2?3))
--     where x = True ? False
--           f (i,a) (b,j) = (i, j, a, b)
--   {-# ORACLE_RESULT goal12: Values [(1, 2, True, True), (1, 2, False, False)] #-}
--   {-# ORACLE_RESULT goal12: Values [(1, 3, True, True), (1, 3, False, False)] #-}
--
-- goal13 :: Values (Int, Int, Bool, Bool)
-- goal13 = evalS (set f $> (1,x) $< (x,2?3))
--     where x = True ? False
--           f (i,a) (b,j) = (i, j, a, b)
--   {-# ORACLE_RESULT goal13: Values [(1, 2, True, True), (1, 2, False, False)] #-}
--   {-# ORACLE_RESULT goal13: Values [(1, 3, True, True), (1, 3, False, False)] #-}

-------------------------------------------
-- Examples with several arguments.

data R3 = F_TTT | F_TTF | F_TFT | F_TFF | F_FTT | F_FTF | F_FFT | F_FFF
        | G_TTT | G_TTF | G_TFT | G_TFF | G_FTT | G_FTF | G_FFT | G_FFF
          deriving Show

f3 True  True  True  = F_TTT
f3 True  True  False = F_TTF
f3 True  False True  = F_TFT
f3 True  False False = F_TFF
f3 False True  True  = F_FTT
f3 False True  False = F_FTF
f3 False False True  = F_FFT
f3 False False False = F_FFF

g3 True  True  True  = G_TTT
g3 True  True  False = G_TTF
g3 True  False True  = G_TFT
g3 True  False False = G_TFF
g3 False True  True  = G_FTT
g3 False True  False = G_FTF
g3 False False True  = G_FFT
g3 False False False = G_FFF

h3 = f3 ? g3
h3' x y z = f3 x y z ? g3 x y z

-- Split on f/g.  (h3) reduces to (f3) and (g3).
goal30 = evalS (set h3  $< x $< y $< z) where x,y,z free
  {-# ORACLE_RESULT goal30: Values [F_FFF, F_FFT, F_FTF, F_FTT, F_TFF, F_TFT, F_TTF, F_TTT] #-}
  {-# ORACLE_RESULT goal30: Values [G_FFF, G_FFT, G_FTF, G_FTT, G_TFF, G_TFT, G_TTF, G_TTT] #-}

-- Split on f/g and the second argument.
goal31 = evalS (set h3  $< x $> y $< z) where x,y,z free
  {-# ORACLE_RESULT goal31: Values [F_FFF, F_FFT, F_TFF, F_TFT] #-}
  {-# ORACLE_RESULT goal31: Values [F_FTF, F_FTT, F_TTF, F_TTT] #-}
  {-# ORACLE_RESULT goal31: Values [G_FFF, G_FFT, G_TFF, G_TFT] #-}
  {-# ORACLE_RESULT goal31: Values [G_FTF, G_FTT, G_TTF, G_TTT] #-}

-- No splits.  (h3') is not reducible.
goal32 = evalS (set h3' $< x $< y $< z) where x,y,z free
  {-# ORACLE_RESULT goal32: Values [F_FFF, F_FFT, F_FTF, F_FTT, F_TFF, F_TFT, F_TTF, F_TTT, G_FFF, G_FFT, G_FTF, G_FTT, G_TFF, G_TFT, G_TTF, G_TTT] #-}

-- Split on the second argument only.
goal33 = evalS (set h3' $< x $> y $< z) where x,y,z free
  {-# ORACLE_RESULT goal33: Values [F_FFF, F_FFT, F_TFF, F_TFT, G_FFF, G_FFT, G_TFF, G_TFT] #-}
  {-# ORACLE_RESULT goal33: Values [F_FTF, F_FTT, F_TTF, F_TTT, G_FTF, G_FTT, G_TTF, G_TTT] #-}

