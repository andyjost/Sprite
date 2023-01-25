data Block = A | B | C | D | E deriving (Show,Eq)
type World = ([Block], [Block], [Block])
type Trace = [World]

solve :: World -> World -> Trace
solve initial final = extend [initial]
  where
    move :: World -> World
    move (x:xs, ys, zs) = (xs, x:ys, zs) ? (xs, ys, x:zs)
    move (xs, y:ys, zs) = (y:xs, ys, zs) ? (xs, ys, y:zs)
    move (xs, ys, z:zs) = (z:xs, ys, zs) ? (xs, z:ys, zs)

    extend :: Trace -> Trace
    extend (t:ts)
      | t == final = reverse (t:ts)
      | elem t ts  = failed
      | otherwise  = extend (move t : t : ts)


main = solve ([A,B],[],[]) ([],[],[A,B])
