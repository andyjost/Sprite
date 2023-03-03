pairs :: [a] -> [b] -> [(a,b)]
pairs xs ys = [ (x,y) | x<-xs, y<-ys ]

main :: [(Int,Int)]
main = pairs [1..100] [1..100]
-- Result: [(1,4),(1,5),(2,4),(2,5),(3,4),(3,5)]
