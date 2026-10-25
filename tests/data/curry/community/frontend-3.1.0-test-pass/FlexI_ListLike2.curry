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

mapGeneral f xs | isEmpty xs = empty
                | otherwise  = let y = headF xs
                                   ys = tailF xs
                               in insert (f y) (mapGeneral f ys)
