-- Programs for unit_chars.py.  The source holds raw UTF-8 as well as
-- escapes.  The goals that touch a file take its name from the test.
module Chars where

import Data.Char

-- A case over character literals.  The rules do not overlap.
classify :: Char -> Int
classify 'a' = 1
classify 'ä' = 2
classify '\246' = 3

sample :: String
sample = "äöü"

shown :: String
shown = unwords (map (show . chr) [228, 160, 127, 126, 128512, 0, 10])

shownString :: String
shownString = show ("a" ++ sample)

readChars :: [Char]
readChars = map read ["'\\228'", "'ä'", "'\\x1F600'", "'\\o344'"]

readString :: String
readString = read "\"\\228\\246\\252\""

cases :: [Int]
cases = map classify "aäö"

narrowed :: Int
narrowed = classify x where x free

readLength :: String -> IO Int
readLength f = readFile f >>= return . length

readText :: String -> IO String
readText f = readFile f

-- The code points of a file.  A malformed byte sequence becomes the
-- replacement character.
readOrds :: String -> IO [Int]
readOrds f = readFile f >>= return . map ord

write :: String -> IO ()
write f = writeFile f "äöü" >> appendFile f (map chr [128512])

-- The characters are computed, not literals.  The C++ writeFile crashed on
-- this: it head-normalized a nested variable whose realpath did not start at
-- the root of the step.
writeComputed :: String -> IO ()
writeComputed f = writeFile f (map toUpper "abä") >> appendFile f (map chr [252, 10])

roundTrip :: String -> IO Int
roundTrip f = writeFile f "äöü😀" >> readFile f >>= return . length

-- The standard streams.  The test runs these in a child process.
putThree :: IO ()
putThree = putChar (chr 228) >> putChar (chr 128512) >> putChar (chr 10)

getOrd :: IO Int
getOrd = getChar >>= return . ord

getTwoOrds :: IO [Int]
getTwoOrds = getChar >>= \a -> getChar >>= \b -> return [ord a, ord b]
