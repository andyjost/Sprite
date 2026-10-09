-- Programs for unit_setfunctions_bugs.py, issue #123: a captured choice
-- that the walk of N reaches through a forward node in front of its box.
-- constT x 0 rewrites to a forward node to the guarded x.  The walk of the
-- Python backend spliced the chain and the guard behind it out together,
-- so the choice was pull-tabbed without its box and encapsulated.
module CapturedFwd where

import Control.SetFunctions

data T = A | B
  deriving (Eq, Ord, Show)

constT :: T -> Int -> T
constT t _ = t

-- The captured choice is reached through the forward node alone.
pickOne :: T -> (Int -> T) -> [T]
pickOne z f = [z] ? [f 0]

oneCaptured :: (Int, T)
oneCaptured = let x = A ? B in
  let vs = sortValues (set2 pickOne A (constT x)) in (length vs, x)

oneCapturedSet :: ([[T]], T)
oneCapturedSet = let x = A ? B in
  let vs = sortValues (set2 pickOne A (constT x)) in (vs, x)

-- The choice is captured and a guarded argument as well.
pickOrBoth :: T -> (Int -> T) -> T -> [T]
pickOrBoth z f y = [z] ? [f 0, y]

-- The values of the capsule are consumed before the outside decides x.
lengthFirst :: (Int, T)
lengthFirst = let x = A ? B in
  let vs = sortValues (set3 pickOrBoth A (constT x) x) in (length vs, x)

-- The whole set before x.
setFirst :: ([[T]], T)
setFirst = let x = A ? B in
  let vs = sortValues (set3 pickOrBoth A (constT x) x) in (vs, x)

-- The outside decides x before the second value.
capturedThenGuarded :: (T, [[T]])
capturedThenGuarded = let x = A ? B in
  let vs = sortValues (set3 pickOrBoth A (constT x) x) in
  (head vs =:= [A]) &> (x, vs)
