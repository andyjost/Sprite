-- Programs for unit_setfunctions_bugs.py: set functions over a free
-- variable that a choice bound, or over a choice the configuration decided
-- (issue #61), set functions whose values are sub-terms of the guarded
-- argument (issue #32), and a choice from a shrinking pool (issue #36).
module SetFunctionsBugs where

import Control.SetFunctions
import Data.List (last, tails)

data T = A | B deriving (Eq, Ord, Show)

-- Issue #61.  A choice binds the variable before the set function sees it.
-- The application of the set function sits below the pull-tab of the
-- constraint, so both alternatives share it.  Each must see its own
-- binding.
boundVar :: [[T]]
boundVar = let t free in (t =:= (A ? B)) &> [sortValues (set1 id t)]

dup :: T -> [T]
dup x = [x, x]

-- The bound variable in two set functions.
twoSets :: [([T], [[T]])]
twoSets = let t free in
  (t =:= (A ? B)) &> [(sortValues (set1 id t), sortValues (set1 dup t))]

inner :: T -> [T]
inner x = sortValues (set1 id x)

-- A set function inside a set function, both over the bound variable.
nestedBound :: [[[T]]]
nestedBound = let t free in (t =:= (A ? B)) &> [sortValues (set1 inner t)]

-- The variable forced to normal form before the set function sees it: the
-- form the examples used before the fix.
forced :: [[T]]
forced = let t free in (t =:= (A ? B)) &> [inner $## t]

forcedStrict :: [[T]]
forcedStrict = let t free in (t =:= (A ? B)) &> [inner $!! t]

constT :: T -> Int -> T
constT x _ = x

-- A choice, not a variable, decides the argument.  The pull-tab of the
-- first component of the pair makes the choice before the set function
-- sees it, and the alternatives share the application.  Each must see its
-- own side.
choiceArg :: (T, [T])
choiceArg = let x = A ? B in (x, sortValues (set1 id x))

-- The decided choice in the function position: captured, not received.
choiceCaptured :: (T, [T])
choiceCaptured = let x = A ? B in (x, sortValues (set1 (constT x) 0))

-- The bound variable behind a call, behind the forward node a forced call
-- leaves, inside a partial application in the function position, and
-- inside a data structure.
viaCall :: [[T]]
viaCall = let t free in (t =:= (A ? B)) &> [sortValues (set1 id (id t))]

viaForward :: [[T]]
viaForward = let t free in let a = id t in
  (t =:= (A ? B)) &> (a `seq` [sortValues (set1 id a)])

viaPartial :: [[T]]
viaPartial = let t free in
  (t =:= (A ? B)) &> [sortValues (set1 (constT t) 0)]

viaData :: [[T]]
viaData = let t free in (t =:= (A ? B)) &> [sortValues (set1 head [t, A])]

-- A literal list longer than the walk of the runtime visits (64 nodes),
-- with the bound variable at its end.  The walk gives up before it reaches
-- the variable and treats the application as private.
longArg :: [[T]]
longArg = let t free in
  let longList =
        [ A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
        , A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
        , A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
        , A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
        , A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
        , t
        ]
  in (t =:= (A ? B)) &> [sortValues (set1 last longList)]

-- The same list without a variable in a deterministic program: the one
-- configuration skips the walk, and the application stays shared.
longPlain :: [T]
longPlain = sortValues (set1 last longPlainList)

longPlainList :: [T]
longPlainList =
  [ A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
  , A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
  , A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
  , A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
  , A, A, A, A, A, A, A, A, A, A, A, A, A, A, A, A
  ]

-- The same list under a configuration that made a choice: the walk runs,
-- gives up at the bound, and the application counts as private in both
-- alternatives.
longPlainChoice :: (T, [T])
longPlainChoice = (A ? B, sortValues (set1 last longPlainList))

-- A set function that starts while u is unbound: its first value is forced
-- before a constraint narrows u, and its second value needs u.  The two
-- alternatives of the constraint share the SetEval node and its queue, and
-- the nested queue reads the fingerprint of the alternative that resumes it
-- first.  A known failure of both backends; see unit_setfunctions_bugs.py.
pickOrCase :: T -> T -> T
pickOrCase x y = x ? (case y of { A -> A; B -> B })

narrowedAfterStart :: [T]
narrowedAfterStart = let u free in
  let vs = valuesOf (set2 pickOrCase A u) in
  (head vs =:= A) &> ((u =:= (A ? B)) &> vs)

-- Issue #32.  The values of the set function are sub-terms of its guarded
-- argument, so the guard reaches the root of the nested configuration.
anyOf :: [a] -> a
anyOf (x:xs) = x ? anyOf xs

anyOfSet :: [Int]
anyOfSet = sortValues (set1 anyOf [1,2,3])

tailsSet :: [[[Int]]]
tailsSet = sortValues (set1 tails [1,2,3])

headOrLastSet :: [Int]
headOrLastSet = sortValues (set1 (\xs -> head xs ? last xs) [1,2,3])

-- Issue #36.  A choice from a shrinking pool.  The rules of the program of
-- the issue overlap: the second matches n = 0 as well, and its recursion
-- never ends, because nothing forces anyOf [] once the pool is empty.
-- PAKCS does not end on it either.  The guard makes the rules exclusive.
assignN :: Int -> [Int] -> [Int] -> [Int]
assignN 0 _ acc = acc
assignN n pool acc | n > 0
  = let d = anyOf pool in assignN (n - 1) (filter (/= d) pool) (d : acc)

pick2 :: [Int]
pick2 = assignN 2 [1,2,3] []

-- The program of the issue, as written.  Its first six values are the six
-- of pick2; after them the evaluation does not end.
assignOverlap :: Int -> [Int] -> [Int] -> [Int]
assignOverlap 0 _ acc = acc
assignOverlap n pool acc
  = let d = anyOf pool in assignOverlap (n - 1) (filter (/= d) pool) (d : acc)

pickOverlap :: [Int]
pickOverlap = assignOverlap 2 [1,2,3] []
