{-# ORACLE_RESULT main () #-}
main :: IO ()
main = catch (writeFile "/" "the content") (\_ -> return ())
