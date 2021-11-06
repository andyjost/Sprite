data Nat = O | I Nat deriving Show

natToInt :: Nat -> Int
natToInt O = 0
natToInt (I n) = 1 + natToInt n

natFromInt :: Int -> Nat
natFromInt i | i == 0    = O
             | otherwise = I (natFromInt (i-1))
