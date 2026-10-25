module Classes where
class Size a where
  size :: a -> Int
instance Size Bool where
  size False = 0
  size True = 1
goal = size True
