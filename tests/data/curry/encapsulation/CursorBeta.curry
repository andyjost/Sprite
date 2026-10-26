module CursorBeta where
data Pair = Pair Bool Bool
loop :: Bool
loop = loop
main :: Pair
main = let e = (x :: Bool) =:= y
       in (e &> Pair True True)
          ? ((x =:<= False) &> (y =:<= True) &> Pair loop e)
  where x,y free
