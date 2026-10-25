{-# LANGUAGE MultiParamTypeClasses, FunctionalDependencies, FlexibleInstances, FlexibleContexts #-}

class ListLike le e | le -> e where
  empty :: le
  insert :: e -> le -> le
  isEmpty :: le -> Bool
  headF :: le -> e
  tailF :: le -> le
  

instance ListLike [a] a where
  empty = []
  insert = (:)
  isEmpty = null
  headF = head
  tailF = tail

and' :: ListLike l Bool => l -> Bool
and' l | isEmpty l = True
       | otherwise = headF l && and' (tailF l)
