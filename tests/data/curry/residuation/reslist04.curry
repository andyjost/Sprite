{-# ORACLE_RESULT main "[2,1]" #-}

list21 :: [Int]
list21 = [x, x=:=2&>1] where x free
main = head $!! [True,x] where x free