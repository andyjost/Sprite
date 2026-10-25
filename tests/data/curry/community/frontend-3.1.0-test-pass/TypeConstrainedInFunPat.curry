-- The argument type of `test` will be inferred as TypeConstrained due to the literal pattern
-- and then defaulted to Int.
-- test1 :: Num a => Int -> a
test1 1 = 1

-- test2 :: Int -> Bool
test2 2 = True

-- Test that the TypeConstrained is not accidentally inserted into the environment,
-- because that would lead to an unhandled TypeConstrained in functional patterns.
-- use :: (Data a, Num a) => a -> Int
-- (Data due to the functional pattern, Num due to the type of test1)
use1 (test1 n) = n
-- use2 :: Int -> Bool
use2 (test2 n) = n

-- Check that the type substitution is applied before defaulting.
-- Argument of replace is some `a` first,
-- which is then substituted to be `[b]` with b TypeConstrained.
-- Then, `b` is defaulted to Int.
-- listify :: [Int] -> Bool
listify (2:p)  = True

useListify1 :: Bool -> Ordering
useListify1 (listify p) = EQ

-- useListify2 :: Bool -> Ordering
useListify2 (listify p) = EQ
