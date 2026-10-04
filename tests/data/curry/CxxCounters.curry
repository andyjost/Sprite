-- Programs for unit_cxx_counters.py: small programs whose scheduler
-- counters (serial steps, lifetimes, shared steps) follow from their steps.
module CxxCounters where

import Control.SetFunctions

-- One configuration from start to end, fewer than 1024 steps.
count :: Int -> Int
count n = if n == 0 then 0 else 1 + count (n - 1)

-- The choice reaches the root after two steps (coinNot, then not pulls the
-- choice up).  The parent forks; each alternative takes one step on the
-- node the parent made, so both of those steps are shared work.
coinNot :: Bool
coinNot = not (True ? False)

-- One alternative fails: failed takes a step, then not forwards to the
-- failure, and the configuration is dropped after two steps.
oneFails :: Bool
oneFails = not (True ? failed)

-- Two values.  A consumer that takes the first one leaves the other
-- alternative in the queue.
twoValues :: Int
twoValues = (1 + 0) ? (2 + 0)

-- Three alternatives inside a set function: two forks and three values in
-- the nested queue, none in the outermost one.
coin :: Int -> Int
coin x = (x + 0) ? (x + 1) ? (x + 2)

inSet :: [Int]
inSet = sortValues (set1 coin 1)
