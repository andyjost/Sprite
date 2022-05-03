{-# ORACLE_RESULT main True #-}

list21 :: [Int]
list21 = [x, x=:=2&>1] where x free
main :: Bool
main = head $!! [True,x] where x free
