{-# ORACLE_RESULT main () #-}
main :: IO ()
main = do appendFile "data/curry/misc/appendFile.out" "Hello"
          appendFile "data/curry/misc/appendFile.out" ", "
          appendFile "data/curry/misc/appendFile.out" "World!"
