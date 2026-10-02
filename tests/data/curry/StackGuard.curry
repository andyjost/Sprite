-- Programs for unit_cxx_stack.py.  Each one nests evaluations deeper than the
-- stack limit of the test allows, or runs a set function in a nested work
-- queue.
module StackGuard where

import Control.SetFunctions

-- Nests one evaluation inside another for every list element.
deep :: Int -> Int
deep n = length [1..n]

-- One alternative between two deep ones.
deepAlt :: Int -> Int
deepAlt n = deep n ? 1 ? deep n

-- Three deep alternatives.  A global progress check does not see that one of
-- them is stuck while the others run.
deepThree :: Int -> Int
deepThree n = deep n ? deep n ? deep n

-- The deep evaluation runs in the nested work queue of a set function.
deepSet :: Int -> Int
deepSet n = foldValues (+) 0 (set1 deep n) ? 1

-- A set function that never ends.  Its queue holds one configuration, so the
-- enclosing queue must rotate.
loop :: Int
loop = loop

divergingSet :: Int
divergingSet = (if isEmpty (set0 loop) then 0 else 1) ? 1

-- An alternative that calls a set function in every iteration.
setLoop :: Int
setLoop = if isEmpty (set0 (1 ? 2)) then 0 else setLoop

setLoopAlt :: Int
setLoopAlt = setLoop ? 1

-- The nested queue holds a diverging head and a finite sibling, and the
-- enclosing queue holds a second alternative.  The nested queue must rotate
-- in place while the enclosing queue rotates, or the set function never
-- produces its value.
nestedChoice :: Int
nestedChoice = (if isEmpty (set0 (loop ? 2)) then 0 else 1) ? loop

-- Walks a list by a tail call, so the nesting stays shallow.
lastOf :: [Int] -> Int
lastOf (x:xs) = if null xs then x else lastOf xs

-- A long finite list.  Copying the value out of the graph must not recurse
-- once per element.
longList :: Int -> [Int]
longList n = [1..n]

-- A deep alternative beside a shallow one that needs many steps.  When the
-- deep one is stuck at the limit, the shallow one must still produce its
-- value.
mixedAlt :: Int -> Int -> Int
mixedAlt n m = deep n ? lastOf [1..m]

-- Many steps at a shallow depth, alone and as two alternatives.  The step
-- counts of the two forms must agree (see unit_cxx_stack.py).
lastOfRange :: Int -> Int
lastOfRange n = lastOf [1..n]

twoLastOf :: Int -> Int
twoLastOf n = lastOfRange n ? lastOfRange n
