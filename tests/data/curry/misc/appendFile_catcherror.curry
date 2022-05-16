{-# ORACLE_RESULT main () #-}
main :: IO ()
main = catch (appendFile "/" "the content") (\_ -> return ())
