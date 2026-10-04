-- Programs for unit_cxx_variable.py: pattern matches that read their
-- arguments through the Variable of the C++ runtime, with and without set
-- guards.  The runtime keeps the path and the guards of a variable inline
-- up to a fixed number and on the heap beyond it.
module CxxVariable where

import Control.SetFunctions

data Nest = Leaf Int | Wrap Nest

-- Twelve constructors in one pattern.  The front end lifts every level into
-- a function of its own, so each step reads one successor of a successor.
-- The leaf builds a fresh value.  (A set function whose value is a sub-term
-- of its argument is covered by unit_cxx_scheduler.py.)
unwrap :: Nest -> Int
unwrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Leaf n))))))))))))) = n + 0

-- A nest built lazily: every level is a function call that the pattern
-- match evaluates, so the slot of each variable holds a forward node once.
wrap :: Int -> Int -> Nest
wrap n x = if n == 0 then Leaf x else Wrap (wrap (n - 1) x)

deep :: Int
deep = unwrap (wrap 12 7)

-- The same depth over a literal value: no evaluation between the levels.
literal :: Int
literal = unwrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Wrap (Leaf 9)))))))))))))

-- Two variables of one pattern.
data Tree = Fork Tree Tree | Tip Int

tips :: Tree -> (Int, Int)
tips (Fork (Fork (Fork (Fork (Fork (Fork (Fork (Fork (Fork (Tip a) (Tip b)) _) _) _) _) _) _) _) _) = (a, b)

grow :: Int -> Tree
grow n = if n == 0 then Fork (Tip 1) (Tip 2) else Fork (grow (n - 1)) (Tip 0)

shared :: (Int, Int)
shared = tips (grow 8)

-- Inside a set function the argument sits behind a set guard, so every
-- variable of the match carries the guard.
setDeep :: [Int]
setDeep = sortValues (set1 unwrap (wrap 12 7))

-- A choice in the argument of the set function is outside it, so the goal
-- has two values.
setChoice :: [Int]
setChoice = sortValues (set1 unwrap (wrap 12 (3 ? 5)))

-- A choice inside the set function gives one set with both values.
unwrapTwice :: Nest -> Int
unwrapTwice x = unwrap x ? (unwrap x + 10)

setInner :: [Int]
setInner = sortValues (set1 unwrapTwice (wrap 12 4))

-- Three set functions, one inside the other.  The innermost match reads the
-- argument through three set guards: more than the inline room of the
-- guard list of a Variable.
inner :: Nest -> [Int]
inner x = sortValues (set1 unwrap x)

middle :: Nest -> [[Int]]
middle x = sortValues (set1 inner x)

nested :: [[[Int]]]
nested = sortValues (set1 middle (wrap 12 7))
