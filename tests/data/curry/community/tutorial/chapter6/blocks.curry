-- "Blocks World" solver for very simple problems

data Block = A | B | C | D | E deriving Eq
type Stack = [Block]
type World = (Stack, Stack, Stack)
type Trace = [World]
data Problem = Problem World World

simpleProblem, difficultProblem :: Problem
simpleProblem = Problem ([A,B],[],[]) ([],[A,B],[])
difficultProblem = Problem ([A,B,C,D,E],[],[]) ([],[C,B,A,D,E],[])

move :: World -> World
move (x:xs, ys, zs) = (xs, x:ys, zs) ? (xs, ys, x:zs) -- p -> q/r
move (xs, y:ys, zs) = (y:xs, ys, zs) ? (xs, ys, y:zs) -- q -> p/r
move (xs, ys, z:zs) = (z:xs, ys, zs) ? (xs, z:ys, zs) -- r -> p/q

extend :: Trace -> World -> Trace
extend trace@(t:ts) goal
  | t == goal    = reverse trace
  | t `elem` ts  = failed
  | otherwise    = extend (move t : trace) goal

main :: Trace
main = extend [s] f where Problem s f = simpleProblem
