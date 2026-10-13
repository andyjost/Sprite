-- Rule N.1 of the Fair Scheme at a failure beside a sibling (issues #132
-- and #136).  The scan reads a failure at its cursor alone, as KiCS2 does
-- (decision D27 of 2026-10-12), not over every successor of a constructor
-- cell before the descent, as the thesis states the rule.  No value
-- depends on the reading: a configuration with a failure under its
-- constructor spine has no value under either one.  The difference is in
-- termination alone.  The goals of the first part end and have tests in
-- unit_n1_cursor.py; the three capture goals among them end since the
-- set0 lift of decision D28 (2026-10-12) boxes the captured t.  The goals
-- of the second part are records: the eager reading ends them and the
-- cursor reading does not; no test runs them.
module FailSib where

import Control.SetFunctions

loop :: Int
loop = loop

-- The control of issue #132: the shape of goal (below) without the
-- diverging sibling.  No value.
goal0 :: (Int, Int)
goal0 = let t = (failed :: Int) in (t ? 1, t)

-- A choice beside the operation failed.  The choice is pulled up, and both
-- children drop after a step at failed.  No value.
goalChoice :: (Int, Int)
goalChoice = (1 ? 2, failed)

-- A failure cell beside a choice.  The first child steps t to a failure
-- and is dropped.  The second child forks at the choice, and both children
-- drop at the failure.  No value.
goalOrder :: (Int, Int)
goalOrder = let t = (failed :: Int) in (t, 0) ? (1 ? 2, t)

-- Controls with values: a choice beside a value, and the shared pair of
-- issue #126, whose dropped alternative changes no cell.
ctrlPair :: (Int, Int)
ctrlPair = (1 ? 2, 3)

ctrlShared :: (Int, Int)
ctrlShared = let p = (failed :: Int, 1) in p ? (snd p, 2)

-- A captured variable of set0 that fails, beside loop.  The compiler lifts
-- set0 (t + 1) over t into set1 L t (decision D28 of 2026-10-12), so t is
-- boxed at the entry of the capsule: its failure is an outside failure of
-- the set function, which fails, and length fails at the cursor before
-- the scan reaches loop.  No value, and the run ends.  (Before the lift,
-- the failure was the function's own, the set was empty, length gave 0,
-- and the scan then stepped loop without end.)
captureShared :: (Int, Int, Int)
captureShared = let t = (failed :: Int) in (length (sortValues (set0 (t + 1))), loop, t)

-- The same with the step at the cursor itself: after demands the length,
-- which fails, so after fails at the cursor.  No value.
captureStep :: (Int, Int)
captureStep = let t = (failed :: Int) in (after (length (sortValues (set0 (t + 1)))), t)

after :: Int -> Int
after n = if n == 0 then loop else loop

-- The same one level down: the failure of length is at the cursor inside
-- the inner pair.  No value.
captureDeep :: ((Int, Int), Int)
captureDeep = let t = (failed :: Int) in ((length (sortValues (set0 (t + 1))), loop), t)

-- Records: runs that the eager N.1 of the thesis ends and the cursor
-- reading of decision D27 does not, as KiCS2; not run by the tests.
--
-- Under the cursor reading the scan enters the diverging successor, the
-- rotation restarts it from the root, and it enters the same successor
-- again; the failure beside it is never at the cursor.  Each run below
-- ended under the look-ahead of 2026-10-12 and does not end now (exit 124
-- under timeout 60 on both backends).

-- The reproducer of issue #132.  Rule D.2 forks (t, t) and (loop, t).  The
-- first child steps t to a failure and is dropped.  The second child
-- steps loop without end.
goal :: (Int, Int)
goal = let t = (failed :: Int) in (t ? loop, t)

-- One level down: the failure is a successor of the inner pair.
goal2 :: ((Int, Int), Int)
goal2 = let t = (failed :: Int) in ((t ? loop, t), 1)

-- The failure comes from a step (head []), through the cell the step
-- leaves.
goalFwd :: (Int, Int)
goalFwd = let t = head ([] :: [Int]) in (t ? loop, t)

-- The shape of goal under an alternative with a value: the value (5, 5) is
-- printed under both readings; the run ends under the eager reading alone.
ctrlOuter :: (Int, Int)
ctrlOuter = (let t = (failed :: Int) in (t ? loop, t)) ? (5, 5)

-- Inside a set function.  The failure of goal is the function's own, so
-- the alternative is dropped (rule SF.5) and the set is empty under the
-- eager reading ([] on both backends); under the cursor reading the
-- capsule steps loop without end.  goalSetArg puts the boxed failure
-- beside an alternative that does not end: the first child meets the boxed
-- failure at its cursor, the capsule records it as an outside failure (the
-- failure rule in its deferred form) and goes on with the second child,
-- (loop, guard failed), which does not end under either reading.
goalSet :: [(Int, Int)]
goalSet = sortValues (set0 goal)

goalSetArg :: [(Int, Int)]
goalSetArg = sortValues (set1 (\x -> (x ? loop, x)) failed)

-- The boxed failure sits behind loop inside the capsule: set1 boxes t, the
-- capsule's configuration (loop, x) is constructor-rooted, and its scan
-- enters loop first and never reaches the box, so the capsule yields no
-- value and does not end; the alternative [(t, t)] is dropped at t.  A
-- limit of the look-ahead of 2026-10-12 as well, which ended neither run.
guardShared :: [(Int, Int)]
guardShared = let t = (failed :: Int) in sortValues (set1 (\x -> (loop, x)) t) ? [(t, t)]
