{-# LANGUAGE FunctionalPatterns #-}
module Funpat where
lastOf (_ ++ [x]) = x
goal = lastOf [1,2,3]
