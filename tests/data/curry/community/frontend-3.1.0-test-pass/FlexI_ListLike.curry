{-# LANGUAGE MultiParamTypeClasses, FunctionalDependencies, FlexibleInstances, FlexibleContexts #-}

class ListLikeF b a | b -> a where
  empty :: b
  insert :: a -> b -> b
  isEmpty :: b -> Bool
  headF :: b -> a
  tailF :: b -> b
  

instance ListLikeF [a] a where
  empty = []
  insert = (:)
  isEmpty = null
  headF (x:_) = x
  tailF (_:xs) = xs

mapGeneral :: (ListLikeF b1 a1, ListLikeF b2 a2) => (a1 -> a2) -> b1 -> b2
mapGeneral f xs | isEmpty xs = empty
                | otherwise  = let y = headF xs
                                   ys = tailF xs
                               in insert (f y) (mapGeneral f ys)
