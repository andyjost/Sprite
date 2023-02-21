-- Missionaries and cannibals with the Constrained Constructor pattern
-- Sergio Antoy
-- Fri Jan 17 13:32:43 PST 2003
-- revised Tue Jan 15 09:29:18 PST 2013

-- Three missionaries and three cannibals want to cross a river
-- with a boat that can hold up to two people.
-- Furthermore, the missionaries, if any, on either bank of the river
-- cannot be outnumbered by the cannibals
-- (otherwise, as the intuition hints, they would be eaten by the cannibals).

-- state of the puzzle:
-- it consists of the number of missionaries and cannibals
-- and the presence of the boat on the initial bank of the river

data State = State Int Int Bool deriving Eq

-- Constrained Constructor on State
-- the number of missionaries and cannibals must be valid, i.e.
-- between 0 and 3 inclusive
-- the number of missionaries and cannibals must be safe, i.e.
-- on each bank he missionaries, if any, on either bank of the river
-- cannot be outnumbered by the cannibals

M = 3
C = 2

makeState m c l | valid && safe = State m c l
   where valid = 0 <= m && m <= M && 0 <= c && c <= C
         safe = c <= m && (C - c) <= (M - m)

-- start and end states of the puzzle
start = makeState M C True
end   = makeState 0 0 False

-- make a move: either 1 or 2 people and the boat move to the other bank

move (State m c True)
  = makeState (m-1) c False
  ? makeState (m-2) c False
  ? makeState m (c-1) False
  ? makeState m (c-2) False
  ? makeState (m-1) (c-1) False
move (State m c False)
  = makeState (m+1) c True
  ? makeState (m+2) c True
  ? makeState m (c+1) True
  ? makeState m (c+2) True
  ? makeState (m+1) (c+1) True

-- path of the puzzle
-- a path is a sequence of state of the puzzle

type Path = [State]

-- Constrained Constructor on Path
-- In any path, any state except the initial one must be
-- obtained from the preceeding state by means of a move
-- and cycles are not allowed.

makePath s p | valid && noCycle = s:p
   where valid   | s =:= move (head p) = True
         noCycle = all (s /=) p

-- extend the path argument to the end state
-- see the Incremental Solution pattern

extend p = if (head p == end) then p
           else extend (makePath unknown p)

-- solve the puzzle

main :: [State]
main = extend [start]
