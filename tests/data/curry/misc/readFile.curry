{-# ORACLE_RESULT main "The contents of a file\n" #-}
main :: IO String
main = readFile "data/curry/misc/readFile.in"
