ordMerge (x:xs) (y:ys) | x==y = x:ordMerge xs ys
                       | x<y  = x:ordMerge xs (y:ys)
                       | x>y  = y:ordMerge (x:xs) ys

hamming = 1:ordMerge (map (*2) hamming)
                     (ordMerge (map (*3) hamming)
                               (map (*5) hamming))

main :: [Int]
main = take 200 hamming

