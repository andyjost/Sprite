-- Peano numbers, the module of example 02 in short.  The driver compiles
-- this text with curry.compile, and the oracle loads it as a module.
data Nat = O | I Nat deriving (Eq, Show)

natFromInt :: Int -> Nat
natFromInt n = if n <= 0 then O else I (natFromInt (n - 1))

natToInt :: Nat -> Int
natToInt O = 0
natToInt (I n) = 1 + natToInt n
