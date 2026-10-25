-- Missionaries and cannibals with the Constrained Constructor pattern
-- Sergio Antoy
-- Fri Jan 17 13:32:43 PST 2003

-- Three missionaries and three cannibals want to cross a river
-- with a boat that can hold up to two people.
-- Furthermore, the missionaries, if any, on either bank of the river
-- cannot be outnumbered by the cannibals
-- (otherwise, as the intuition hints, they would be eaten by the cannibals).

-- state of the puzzle:
-- it consists of the number of missionaries and cannibals
-- and the presence of the boat on the initial bank of the river

data State = State Int Int Bool Int Int

-- Constrained Constructor on State
-- the number of missionaries and cannibals must be valid, i.e.
-- between 0 and 3 inclusive
-- the number of missionaries and cannibals must be safe, i.e.
-- on either bank of the river the missionaries, if any,
-- cannot be outnumbered by the cannibals

makeState m c b n d | valid && safe = State m c b n d
   where valid = 0 <= m && 0 <= c && 0 <= n && 0 <= d -- all positive
         safe  = (m == 0 || m >= c) && (n == 0 || n >= d)

-- start and end states of the puzzle

start m c = makeState m c True  0 0
end   m c = makeState 0 0 False m c

-- make a move: either 1 or 2 people and the boat move to the other bank

move (State m c True  n d) = makeState (m-1) c     False (n+1) d
move (State m c True  n d) = makeState (m-2) c     False (n+2) d
move (State m c True  n d) = makeState m     (c-1) False n     (d+1)
move (State m c True  n d) = makeState m     (c-2) False n     (d+2)
move (State m c True  n d) = makeState (m-1) (c-1) False (n+1) (d+1)
move (State m c False n d) = makeState (m+1) c     True  (n-1) d
move (State m c False n d) = makeState (m+2) c     True  (n-2) d
move (State m c False n d) = makeState m     (c+1) True  n     (d-1)
move (State m c False n d) = makeState m     (c+2) True  n     (d-2)
move (State m c False n d) = makeState (m+1) (c+1) True  (n-1) (d-1)

-- path of the puzzle
-- a path is a sequence of state of the puzzle

type Path = [State]

-- Constrained Constructor on Path
-- In any path, any state except the initial one must be
-- obtained from the preceeding state by means of a move
-- and cycles are not allowed.

makePath s p | valid && noCycle = s:p
   where valid   = s == move (head p)
         noCycle = all (/=s) p

-- extend the path argument to the end state
-- see the Incremental Solution pattern

extend e (s:p) = if (s == e) then s:p
                 else extend e (makePath (move s) (s:p))

-- solve the puzzle
goal m c = length (extend (end m c) [start m c])

main = goal 11 10
