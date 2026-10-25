infixl 8 **

(**) :: Int -> Int -> Int
a ** b | b >= 0 = 
  let accum x y z | z == 0    = x
                  | otherwise =
                       let aux = if (z `mod` 2 == 1)
                                 then x * y
                                 else x
                       in  accum aux (y * y) (z `div` 2)
  in  accum 1 a b


main :: [Int]
main = map (2**) [0,10,20,30,40]
-- expect: [1,1024,1048576,1073741824,1099511627776]
