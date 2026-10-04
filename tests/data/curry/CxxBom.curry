-- The module behind unit_cxx_bom.py.  Its bill of materials holds a
-- metadata value of each kind: the operator carries an integer (all.flags),
-- the alias carries a string (all.alias_target), and the IO action carries a
-- true bool (all.monadic).  The function area is private.
module CxxBom (Shape(..), (+++), plus, greet, main) where

import Data.Maybe (fromMaybe)

data Shape = Circle Int | Square Int Int | Dot

infixl 6 +++
(+++) :: Int -> Int -> Int
a +++ b = a + b

plus :: Int -> Int -> Int
plus a b = a +++ b

greet :: IO ()
greet = putStrLn "hi"

area :: Shape -> Int
area (Circle r) = 3 * r * r
area (Square a b) = a * b
area Dot = 0

main :: Int
main = area (Square 2 3) +++ plus 1 (fromMaybe 0 (Just 2))
