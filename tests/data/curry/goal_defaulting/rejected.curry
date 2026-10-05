-- Goals the defaulting table of the PAKCS REPL rejects: an Enum constraint
-- alone, and Bounded with Num.  Both systems refuse to evaluate them with
-- the sentence "Cannot handle arbitrary overloaded top-level expressions".
-- func_goal_defaulting.py runs this file as an intended failure, so the
-- oracle never runs it.

goal1 = toEnum 65                        -- Enum a => a
goal2 = maxBound + 1                     -- (Bounded a, Num a) => a
