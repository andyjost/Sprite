{-# ORACLE_RESULT main 6 #-}
-- The file holds UTF-8; length counts code points, not bytes.
main :: IO Int
main = readFile "data/curry/io/readFile_utf8.in" >>= return . length
