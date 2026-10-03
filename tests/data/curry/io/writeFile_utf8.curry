{-# ORACLE_RESULT main () #-}
-- The characters are written as UTF-8.
main :: IO ()
main = writeFile "data/curry/io/output_utf8.txt" "äöü😀"
