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
-- alternatives of the constraint share the SetEval node and its queue.
-- The choice of the generator of u escapes the capsule (rule SF.1), and
-- each alternative prunes it to its side; see unit_setfunctions_bugs.py.
pickOrCase :: T -> T -> T
pickOrCase x y = x ? (case y of { A -> A; B -> B })

narrowedAfterStart :: [T]
narrowedAfterStart = let u free in
  let vs = valuesOf (set2 pickOrCase A u) in
  (head vs =:= A) &> ((u =:= (A ? B)) &> vs)

-- The shapes of the repair at the escape (TestResumedCapsule).  Every
-- capsule below starts before the choice or the variable is decided, gives
-- its first value, and resumes under the alternatives.

-- The variable inside a data structure: the second value is the variable
-- at the root of the capsule.
pickOrHead :: T -> [T] -> T
pickOrHead x ys = x ? head ys

narrowedInData :: [T]
narrowedInData = let u free in
  let vs = valuesOf (set2 pickOrHead A [u]) in
  (head vs =:= A) &> ((u =:= (A ? B)) &> vs)

-- A choice of the argument decided outside after the capsule started: the
-- first component of the pair decides x, and the second value needs x.
choiceAfterStart :: (T, [T])
choiceAfterStart = let x = A ? B in
  let vs = valuesOf (set2 pickOrCase A x) in
  (head vs =:= A) &> (x, vs)

-- Two capsules over one variable, both consumed in part before the
-- constraint narrows it.
twoCapsules :: ([T], [T])
twoCapsules = let u free in
  let vs = valuesOf (set2 pickOrCase A u)
      ws = valuesOf (set2 pickOrCase B u)
  in (head vs =:= A) &> (head ws =:= B) &> ((u =:= (A ? B)) &> (vs, ws))

-- A nested set function.  The inner capsule, over the variable, is in the
-- value of the outer set function and outlives it.
inner2 :: T -> [T]
inner2 y = valuesOf (set2 pickOrCase A y)

nestedAfterStart :: [[T]]
nestedAfterStart = let u free in
  let vs = valuesOf (set1 inner2 u) in
  (head (head vs) =:= A) &> ((u =:= (A ? B)) &> vs)

-- A set function inside the argument of a set function, the inner one over
-- the variable.
argAfterStart :: [[T]]
argAfterStart = let u free in
  let vs = valuesOf (set1 id (valuesOf (set2 pickOrCase A u))) in
  (head (head vs) =:= A) &> ((u =:= (A ? B)) &> vs)

-- The escape of a choice the outside has not decided: the second value
-- needs the choice of the argument, and the outside forks on it.
escapeUndecided :: [T]
escapeUndecided = let vs = valuesOf (set2 pickOrCase A (A ? B)) in
  (head vs =:= A) &> vs

-- The captured shapes: the choice or the variable comes through the
-- function position, not through a guarded argument, so it is in no escape
-- set.  The outside decides it after the capsule started, and the capsule
-- gives each alternative the value of its side, as the call-time reading
-- of choiceCaptured does (a choice an enclosing configuration decided
-- escapes too; see choice_escapes).
pickOrCall :: T -> (Int -> T) -> T
pickOrCall z f = z ? f 0

capturedChoiceAfterStart :: (T, [T])
capturedChoiceAfterStart = let x = A ? B in
  let vs = valuesOf (set2 pickOrCall A (constT x)) in
  (head vs =:= A) &> (x, vs)

capturedVarAfterStart :: [T]
capturedVarAfterStart = let u free in
  let vs = valuesOf (set2 pickOrCall A (constT u)) in
  (head vs =:= A) &> ((u =:= (A ? B)) &> vs)

-- The captured occurrence of x is reached before the guarded one.
pickOrBoth :: T -> (Int -> T) -> T -> [T]
pickOrBoth z f y = [z] ? [f 0, y]

capturedThenGuarded :: (T, [[T]])
capturedThenGuarded = let x = A ? B in
  let vs = valuesOf (set3 pickOrBoth A (constT x) x) in
  (head vs =:= [A]) &> (x, vs)

-- The outer capsule stays alive and shared: its second value consumes the
-- second value of the inner capsule, over the variable or the choice,
-- after the outside decided it.  The escape from the inner capsule reaches
-- a configuration of the outer one, which must not take a side read from
-- the outside: it escapes the choice in turn (owns_decision).
inner3 :: T -> T
inner3 y = let ws = valuesOf (set2 pickOrCase A y) in head ws ? (ws !! 1)

nestedAlive :: [T]
nestedAlive = let u free in
  let vs = valuesOf (set1 inner3 u) in
  (head vs =:= A) &> ((u =:= (A ? B)) &> vs)

nestedAliveChoice :: (T, [T])
nestedAliveChoice = let x = A ? B in
  let vs = valuesOf (set1 inner3 x) in
  (head vs =:= A) &> (x, vs)

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
