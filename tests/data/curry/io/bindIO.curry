{-# ORACLE_RESULT main 2 #-}
main :: IO Int
main = do
         a <- return 1
         return (a + 1)
