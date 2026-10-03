-- Literals that the test corpus does not contain: negative numbers, float
-- exponents, characters outside ASCII, and literal patterns of every kind.
module Literals where

negInt :: Int
negInt = -1

negFloat :: Float
negFloat = -2.5

bigInt :: Int
bigInt = 12345678901234567890

tiny :: Float
tiny = 1.0e-5

huge :: Float
huge = 1.0e22

floats :: [Float]
floats = [0.1, 100.0, 0.0001, 10000000.0, 1.5e15, 1.5e16, 123456789012345678.0
         , 0.000123, 1e-4, 3.0e-3, 2.0e-300, 5.0e-324]

uni :: String
uni = "\228\246\252 \955 \128512 \t\"\\ \1 \31 \127 \128 \160 \255 ' end"

chars :: [Char]
chars = ['\'', '"', '\\', '\n', '\0', '\31', '\127', '\128', '\955', '\128512'
        , ' ', '~', '\a', '\b', '\v', '\f', '\r', '\DEL', '\NUL', '\SO', '\US']

emptyString :: String
emptyString = ""

intCase :: Int -> Int
intCase n = case n of
  0 -> 10
  (-1) -> 20
  1000000 -> 30
  _ -> 40

negPattern :: Int -> Bool
negPattern (-7) = True
negPattern 7 = False

floatCase :: Float -> Int
floatCase x = case x of
  0.0 -> 1
  (-0.5) -> 2
  1.0e10 -> 3
  _ -> 4

charCase :: Char -> Int
charCase c = case c of
  'a' -> 1
  '\'' -> 2
  '"' -> 3
  '\955' -> 4
  '\n' -> 5
  _ -> 6

stringCase :: String -> Int
stringCase s = case s of
  "" -> 0
  "ab" -> 1
  _ -> 2

negInArg :: Int -> Int
negInArg x = x + (-3) * negate x - (-4.5 `seq` 0)
