{-# ORACLE_RESULT main 'a' #-}
main :: IO Char
main = catch getChar (\_ -> return 'a')
