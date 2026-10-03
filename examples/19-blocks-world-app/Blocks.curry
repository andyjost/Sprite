-- Blocks World as a command-line application.
--
-- A world is three stacks of blocks.  A move takes the top block of one
-- stack and puts it on another stack.  The function plan means every trace
-- of at most n moves that leads from a start world to a goal world and
-- visits no world twice.  Python asks for a plan under the bounds 0, 1, 2,
-- ... and takes the first plan it gets.  The first bound with a plan gives a
-- shortest plan.

data Block = A | B | C | D | E
  deriving (Show, Eq)

-- The three stacks.  The head of each list is the top block of that stack.
type World = ([Block], [Block], [Block])

-- The worlds of a plan, from the start world to the goal world.
type Trace = [World]

-- One legal move.  Each rule matches one source stack and offers a choice of
-- the two target stacks.  The rules overlap, so a world with k non-empty
-- stacks has 2k moves, and move w means every one of them.
move :: World -> World
move (x:xs, ys, zs) = (xs, x:ys, zs) ? (xs, ys, x:zs)
move (xs, y:ys, zs) = (y:xs, ys, zs) ? (xs, ys, y:zs)
move (xs, ys, z:zs) = (z:xs, ys, zs) ? (xs, z:ys, zs)

-- A trace of at most n moves from start to goal.  The search keeps the
-- worlds visited so far, newest first.  A world that repeats an earlier one
-- fails, so that branch of the search ends without a value.  So does a
-- branch that uses up its moves before it reaches the goal.
plan :: Int -> World -> World -> Trace
plan n start goal = search n [start]
  where
    search :: Int -> Trace -> Trace
    search k (w:ws)
      | w == goal = reverse (w:ws)
      | k > 0     = let w' = move w
                    in if w' `elem` ws then failed else search (k - 1) (w' : w : ws)

-- A goal for sprite-exec: every plan of at most five moves that carries
-- three blocks from the first stack to the third stack in the same order.
main :: Trace
main = plan 5 ([A, B, C], [], []) ([], [], [A, B, C])
