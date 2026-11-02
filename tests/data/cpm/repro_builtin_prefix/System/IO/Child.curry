module System.IO.Child where
import System.IO
value :: IO Bool
value = hIsEOF stdin
