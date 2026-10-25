{-# LANGUAGE MultiParamTypeClasses, FunctionalDependencies, FlexibleInstances #-}


class Collects e ce | ce -> e where
  empty :: ce
  insert :: e -> ce -> ce

instance Collects a [a] where
  empty = []
  insert = (:)
