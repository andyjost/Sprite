triangle :: Int -> [(Int,Int)]
triangle n = [ (x,y) | x <- [1..n], y <- [1..x] ]

main :: [(Int,Int)]
main = triangle 300
-- Result: [(1,1),(2,1),(2,2),(3,1),(3,2),(3,3)]
