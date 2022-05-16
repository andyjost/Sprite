{-# ORACLE_RESULT main () #-}
main :: IO ()
main = do appendFile "data/curry/io/appendFile.out" "Hello"
          appendFile "data/curry/io/appendFile.out" ", "
          appendFile "data/curry/io/appendFile.out" "World!"
