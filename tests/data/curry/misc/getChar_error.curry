{-# ORACLE_RESULT main () #-}
-- The test driver feeds this test a stdin with zero bytes.
main :: IO Char
main = getChar
