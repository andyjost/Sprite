-- The program of issue #124 (unit_cxx_runtime.py).  One alternative binds
-- the free variable x with =:<= and reads it; another narrows x.  The first
-- alternative then meets the generator of the variable it bound, and the
-- runtime applies the binding at the fork with its own table of &>
-- (RuntimeState::apply_binding).  The compiled Prelude wrote its table of
-- seq over that table when it was loaded, under the symbol the two shared,
-- so a process that unloaded the object at a reload into interpret:all
-- died at the step of that node.
module ReloadBinding where

len0 :: [Int] -> Int
len0 [] = 0
len0 (_ : _) = 1

bound :: Int
bound = (x =:<= [1, 2] &> (length x ? 7)) ? len0 x
  where x free

bound3 :: Int
bound3 = (x =:<= [1, 2, 3] &> (length x ? 9)) ? len0 x
  where x free
