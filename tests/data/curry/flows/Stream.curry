module Stream where

-- A copy of stage A's Stream (tests/data/boundary/30-generator-contract)
-- with two more goals for F3: partial and mixedL.

three :: Int
three = 1 ? 2 ? 3

mixed :: Int
mixed = 1 ? error "boom" ? 2

nothing :: Int
nothing = failed

-- An alternative that fails after one succeeded.
partial :: Int
partial = 1 ? failed ? 2

-- The left association: the error is not the last alternative of the tree.
mixedL :: Int
mixedL = (1 ? error "boom") ? 2
