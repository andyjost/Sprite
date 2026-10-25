module HaskellRecords where

data R1 a = C { l :: Int, x :: a }
          | D { l :: Int }

-- construction
r1 :: R1 Bool
r1 = C { l = 42, x = True }

r2 :: Data a => R1 a
r2 = C {}

-- pattern matching
fun :: R1 a -> Bool
fun C { l = 42 } = True

fun2 :: R1 a -> Bool
fun2 C {} = False

-- update
upd :: R1 Bool -> R1 Bool
upd r = r { x = False, l = 0 }

-- selection
getL :: R1 a -> Int
getL r = l r

data R2 = E { label :: Int, l2 :: Bool }

r :: R2
r = E { label = 42, l2 = True }

r' :: R2
r' = r { label = 73 }

unr :: R2
unr = E { l2 = True }
