{-# LANGUAGE MultiParamTypeClasses,FunctionalDependencies #-}

class ListLikeF le e where
  insertF :: e -> le -> le
  headF :: le -> e


insHead' e l = headF (insertF e l)

f x y = insertF x . insertF y
