-- The look-ahead of rule N.1 of the Fair Scheme (issue #132).  Rule N.1
-- reads every successor of a constructor cell before the scan descends into
-- one of them: a failure among them, read through forward cells, means that
-- the configuration has no value, and the configuration is dropped before
-- any step below the cell.  Without the look-ahead both backends entered a
-- diverging successor first, the rotation restarted the scan from the root,
-- and the scan entered the same successor again.  The tests are in
-- unit_n1_lookahead.py.
module FailSib where

import Control.SetFunctions

loop :: Int
loop = loop

-- The reproducer.  Rule D.2 forks (t, t) and (loop, t).  The first child
-- steps t to a failure and is dropped.  The second child is dropped at its
-- dispatch, before any step at loop.  No value; the run ends (KiCS2 does
-- not end).
goal :: (Int, Int)
goal = let t = (failed :: Int) in (t ? loop, t)

-- The control: the same shape without the diverging sibling.  No value.
goal0 :: (Int, Int)
goal0 = let t = (failed :: Int) in (t ? 1, t)

-- One level down: the failure is a successor of the inner pair.
goal2 :: ((Int, Int), Int)
goal2 = let t = (failed :: Int) in ((t ? loop, t), 1)

-- The failure comes from a step (head []), through the cell the step
-- leaves.
goalFwd :: (Int, Int)
goalFwd = let t = head ([] :: [Int]) in (t ? loop, t)

-- A control: a choice beside the operation failed.  The operation is not
-- a failure cell until it is stepped, so the look-ahead finds nothing, the
-- choice is pulled up, and both children drop after a step at failed.  No
-- value, before the change as well.
goalChoice :: (Int, Int)
goalChoice = (1 ? 2, failed)

-- Rule N.1 before the pull-tab.  The first child steps t to a failure and
-- is dropped.  The second child holds the failure cell beside a choice: it
-- is dropped at the root without a fork (the look-ahead runs before the
-- scan reaches the choice).  No value; the run ended before the change as
-- well, with a fork and two dropped children.
goalOrder :: (Int, Int)
goalOrder = let t = (failed :: Int) in (t, 0) ? (1 ? 2, t)

-- The parent cell is read again at the first descent after a completed
-- step.  The capsule of set0 rewrites the shared t to a failure (the
-- failure is the function's own, the set is empty, length gives 0); the
-- scan then advances to loop, and the read of the triple finds the failure
-- at successor 2.  No value; without the read again the run did not end,
-- as one configuration never rotates.
captureShared :: (Int, Int, Int)
captureShared = let t = (failed :: Int) in (length (sortValues (set0 (t + 1))), loop, t)

-- The same with the step at the cursor itself: after rewrites itself to
-- loop once the capsule ran, and the read of the pair finds the failure
-- before the next descent at the same cursor.  No value.
captureStep :: (Int, Int)
captureStep = let t = (failed :: Int) in (after (length (sortValues (set0 (t + 1)))), t)

after :: Int -> Int
after n = if n == 0 then loop else loop

-- The limits of the rule, not run by the tests (both runs do not end).
-- captureDeep: the failure appears beside a cell above the parent of the
-- cursor; the runtime reads that cell at its extension alone, and one
-- configuration never rotates back to the root.  guardShared: the failure
-- sits behind a set guard (the argument of set1); the look-ahead does not
-- read through a guard, which belongs to the set-function failure path.
captureDeep :: ((Int, Int), Int)
captureDeep = let t = (failed :: Int) in ((length (sortValues (set0 (t + 1))), loop), t)

guardShared :: [(Int, Int)]
guardShared = let t = (failed :: Int) in sortValues (set1 (\x -> (loop, x)) t) ? [(t, t)]

-- The shape of goal under an alternative with a value: the value is
-- printed and the run ends.
ctrlOuter :: (Int, Int)
ctrlOuter = (let t = (failed :: Int) in (t ? loop, t)) ? (5, 5)

-- Controls with values: a choice beside a value, and the shared pair of
-- issue #126, whose dropped alternative changes no cell.
ctrlPair :: (Int, Int)
ctrlPair = (1 ? 2, 3)

ctrlShared :: (Int, Int)
ctrlShared = let p = (failed :: Int, 1) in p ? (snd p, 2)

-- Inside a set function.  The failure of goal is the function's own, so
-- the alternative is dropped (rule SF.5) and the set is empty: both
-- backends give [].  goalSetArg is a control of the boxed-failure path:
-- the argument of the set function fails, the first child meets the boxed
-- failure at its cursor and fails the whole set function under the
-- default 'escape' before the diverging child runs (no value, before the
-- change as well).  KiCS2 ends neither run, so the tests assert the end
-- of the run alone.
goalSet :: [(Int, Int)]
goalSet = sortValues (set0 goal)

goalSetArg :: [(Int, Int)]
goalSetArg = sortValues (set1 (\x -> (x ? loop, x)) failed)
