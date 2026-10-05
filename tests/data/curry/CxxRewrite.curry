-- Programs for unit_cxx_rewrite.py: the in-place rewrite of the C++ backend.
module CxxRewrite where

data Three = Three Int Int Int
data Color = Red | Green
data Nat = Z | S Nat

-- A tail call whose result fits the redex: the node is written in place.
walk :: [Int] -> Int
walk (_:xs) = walk xs
walk [] = 0

-- A constructor result that fits the redex.
just :: Int -> Maybe Int
just x = Just x

-- A result larger than the redex: the redex is forwarded to a new node.
three :: Int -> Three
three x = Three x x x

-- A reference result: the redex takes a copy of a primitive value, and is
-- forwarded to any other node.
first :: [Int] -> Int
first (x:_) = x

-- A pinned constructor: the redex is forwarded to the static node.
pinned :: Int -> Bool
pinned _ = True

-- A nullary constructor of the program: written in place.
color :: Int -> Color
color _ = Red

-- A literal result: the boxed value is written into the redex.
lit :: Int -> Int
lit _ = 5

-- The arguments change places.  Both are read before the redex is written.
swap :: Int -> Int -> (Int, Int)
swap x y = (y, x)

-- A tail call that rotates its arguments.  rot 1 2 3 (nat 4) is 2.  (A
-- case on an Int literal is lifted into a function of one more argument by
-- the front end, so the counter is a Nat.)
rot :: Int -> Int -> Int -> Nat -> Int
rot x _ _ Z = x
rot x y z (S n) = rot y z x n

nat :: Int -> Nat
nat n = if n == 0 then Z else S (nat (n - 1))

-- A partial application completed by apply.  applyTwice x is x + 2.
plus :: Int -> Int -> Int
plus a b = a + b

plusOne :: Int -> Int
plusOne = plus 1

twice :: (Int -> Int) -> Int -> Int
twice f x = f (f x)

applyTwice :: Int -> Int
applyTwice x = twice plusOne x

-- An endless loop of in-place steps beside a value.  Every step allocates
-- the next sum and leaves no forward node.  The periodic rotation gives the
-- alternative its turn: the first value of fair is 42.
loop :: Int -> Int
loop n = loop (n + 1)

fair :: Int
fair = loop 0 ? 42
