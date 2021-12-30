{-# ORACLE_RESULT main !suspend #-}

list21 :: [Int]
list21 = [x, x=:=2&>1] where x free
main = show list21