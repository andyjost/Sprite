-- Programs for unit_show.py: a shared, acyclic list printed twice (issue
-- #119).  Found by the differential harness (class FS-x, seed 119, reduced
-- by hand).  The C++ printer wrote "..." for the second occurrence of d.
module SharedListPrinter where

goal :: ([Bool], [Bool])
goal = let d = [False] in (d, d)

goal2 :: ([Bool], [Bool], Int)
goal2 = let d = ([False] ? []) in (d, d, 1)
