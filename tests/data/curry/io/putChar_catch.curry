{-# ORACLE_RESULT main () #-}
main :: IO ()
main = catch (putChar 'a') (\_ -> writeFile "data/curry/io/putChar_catch.out" "yes")
