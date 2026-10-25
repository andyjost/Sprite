f :: Int -> Int
f x = x + 1
  where
    h :: Bool -> Bool
    h x = not x

g y = h y * k y
  where
    h a = a * 2
    h :: Int -> Int
    k b = b `div` 2

