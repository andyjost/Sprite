{-# ORACLE_RESULT main 121 #-}
-- Covers a 2023 report by Michael Hanus: readFile combined with bind.  The
-- input file holds the 121 bytes of Peano.curry, the file in the report.
main :: IO Int
main = readFile "data/curry/io/readFile_bind.in" >>= return . length
