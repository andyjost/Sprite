-- Scheduling tasks fed from Python data.
--
-- A task has a name, a duration, and a resource.  A schedule gives every task
-- a start slot.  A schedule is valid when every precedence holds and when two
-- tasks that share a resource do not overlap.  The function schedule means
-- every valid schedule that fits a horizon.

-- A task: (name, duration, resource).
type Task = (String, Int, String)

-- Generate and test.  Each task starts anyOf the slots that keep it inside the
-- horizon, so starts is a choice among every assignment.  The guard keeps the
-- assignments that meet every precedence and have no overlap on a shared
-- resource.  The runtime finds every schedule that passes.
--
-- The runtime makes a choice only when the guard needs its value.  The
-- precedence check comes first because it prunes early: a task that starts
-- too soon fails before any later task gets a start.
schedule :: [Task] -> [(String, String)] -> Int -> [(String, Int)]
schedule tasks prec horizon
  | all ordered prec && all noOverlap [ (a, b) | a <- tasks, b <- tasks, a < b ] = starts
  where
    starts = [ (n, anyOf [0 .. horizon - d]) | (n, d, _) <- tasks ]
    startOf n = case lookup n starts of Just s -> s
    durOf n = head [ d | (m, d, _) <- tasks, m == n ]
    -- The first task ends before the second starts.
    ordered (a, b) = startOf a + durOf a <= startOf b
    -- Two tasks on one resource run one after the other.  The condition a < b
    -- in the guard names each unordered pair of tasks once.
    noOverlap ((a, da, ra), (b, db, rb)) =
      ra /= rb || startOf a + da <= startOf b || startOf b + db <= startOf a
