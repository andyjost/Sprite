{-# LANGUAGE MultiParamTypeClasses, FlexibleInstances, FlexibleContexts #-}

class Nullary where
  g :: Int
  

showg :: Nullary => String
showg = show g

getG :: Nullary => Int
getG = g
