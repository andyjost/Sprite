-- Programs for unit_cxx_freevars.py.
module CxxFreeVars where

data Bit = O | I

-- The alternative O of a narrowed variable counts one; I fails.
bit :: Bit -> Int
bit O = 1
bit I = failed

num :: Bit -> Int
num O = 1
num I = 2

same :: Bit -> Bit
same O = O
same I = I

-- Narrows n fresh variables one after the other, by a case.  The
-- accumulator is forced at every step, so no thunk keeps a variable.
narrowMany :: Int -> Int
narrowMany n = loop n 0
 where
  loop k acc = if k == 0 then acc
               else let x free in loop (k - 1) $! (acc + bit x)

-- The same for each item of a list.  A test feeds the items from Python
-- and reads the counters of the collector between them.
narrowEach :: [Int] -> Int
narrowEach xs = foldr (\k acc -> narrowMany k + acc) 0 xs

-- Binds n fresh variables one after the other, by unification with a
-- constructor, which narrows the variable.
bindMany :: Int -> Int
bindMany n = loop n 0
 where
  loop k acc = if k == 0 then acc
               else let x free in (x =:= O) &> (loop (k - 1) $! (acc + 1))

-- Unifies two fresh variables and narrows one of them, n times.  The group
-- of the two names both ids in the strict constraints of the configuration.
uniteMany :: Int -> Int
uniteMany n = loop n 0
 where
  loop k acc = if k == 0 then acc
               else let x, y free in
                 (x =:= y) &> (loop (k - 1) $! (acc + bit y))

-- A free variable that reaches Python in a value, twice.
pairFree :: (Bit, Bit)
pairFree = let x free in (x, x)

-- Narrows the two components of a pair.  For pairFree, whose components are
-- one variable, the values are 2 and 4.
both :: (Bit, Bit) -> Int
both (x, y) = num x + num y

-- After y =:= x, the root of the group stands for both: the value is y.
groupRoot :: Bit
groupRoot = let x, y free in (y =:= x) &> x

-- The first alternative waits on x (ensureNotFree residuates on a free
-- variable); the second narrows x.  The generator of x lives in its node,
-- so the first alternative wakes and narrows x the same way.
wakeByNarrowing :: Bit
wakeByNarrowing = let x free in ensureNotFree x ? same x

-- The same, with x in a group whose root y leaves the expression once the
-- constraint is consumed.  The residual names both.
wakeInGroup :: Bit
wakeInGroup = let x, y free in (y =:= x) &> (ensureNotFree x ? same x)

data Tri = A | B | C

code :: Tri -> Int
code A = 1
code B = 2
code C = 3

-- x, y, and z are one variable: y is the root of the group (y =:= x unites
-- y with x, and z =:= y adds z).  The expression holds y no more once the
-- constraints are consumed.  The generator of x goes to y at the fork of
-- the generator of x, and z takes it from y when z is narrowed, so x and z
-- agree: the values are (1, 1), (2, 2), and (3, 3).  A table that dropped y
-- would narrow z apart from x.
triple :: (Int, Int)
triple = let x, y, z free in (y =:= x) &> ((z =:= y) &> (code x, code z))

-- A functional pattern binds the variable of the pattern by =:<=, a binding
-- keyed by the id of the variable; the variables under (++) are narrowed.
lastOf :: [Int] -> Int
lastOf (_ ++ [x]) = x

lasts :: Int -> [Int]
lasts n = [ lastOf [1 .. k] | k <- [1 .. n] ]

-- Programs for the finalizer of the generator nodes (TestFinalizers).

total :: [Int] -> Int
total xs = foldr (+) 0 xs

firstTwo :: [Int] -> [Int]
firstTwo xs = take 2 xs
