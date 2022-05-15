{-# ORACLE_RESULT main () #-}
main :: IO ()
main = catch (ioError $ userError "failed") (\_ -> putStrLn "Caught an error")
