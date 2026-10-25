module BigIntegers where

import Data.List (product)
import qualified Numeric

promotion :: [Int]
promotion = [9223372036854775807 + 1, -9223372036854775808 - 1,
             9223372036854775807 * 2, negate (-9223372036854775808)]

demotion :: [Int]
demotion = [9223372036854775808 - 1, -9223372036854775809 + 1,
            9223372036854775808 * 0, 18446744073709551616 `div` 4,
            9223372036854775808 `quot` 2, 9223372036854775808 `rem` 3,
            9223372036854775808 `mod` 3]

divisions :: [(Int,Int,Int,Int)]
divisions = [(x `div` y, x `mod` y, x `quot` y, x `rem` y)
            | x <- [1000000000000000000000000000001,-1000000000000000000000000000001,5,-5],
              y <- [3,-3,1000000000000000000000000000000,-1000000000000000000000000000000]]

powers :: [Int]
powers = [2^63, 2^200, 10^30, product [1..30]]

fib :: Int -> Int
fib n = go n 0 1
 where go k a b = if k == 0 then a else go (k-1) b (a+b)

fibonacci :: Int
fibonacci = fib 100

conversions :: [Int]
conversions = [truncate 1e30, round 1e30, floor 1e30, ceiling 1e30,
               succ 9223372036854775807, pred (-9223372036854775808),
               toEnum 1000000000000000000000000000000,
               fromEnum 1000000000000000000000000000000]

roundtrips :: [Int]
roundtrips = [read (show x) | x <- [10^30, -(10^30), 2^200, -(2^200)]]

unification :: Int
unification = x =:= 10^30 &> x where x free

patternMatch :: Int -> Int
patternMatch 1000000000000000000000000000000 = 1
patternMatch 7 = 2

patternValues :: [Int]
patternValues = [patternMatch (10^30), patternMatch 7]

ordering :: [Bool]
ordering = [10^30 == 1000000000000000000000000000000,
            10^30 /= 10^30 + 1, 10^30 > 2^63, -(10^30) < -(2^63),
            2^63 <= 2^63, -(2^63) >= -(10^30), compare (10^30) (2^63) == GT]

unary :: [Int]
unary = [abs (-9223372036854775808), negate (-9223372036854775808),
         signum (10^30), signum (-(10^30))]

pairedDivisions :: [(Int,Int)]
pairedDivisions = [divMod (-(10^30+1)) 3, quotRem (-(10^30+1)) 3]

numericReads :: [(Int,String)]
numericReads = Numeric.readInt "-1000000000000000000000000000000!" ++
               Numeric.readNat "1000000000000000000000000000000!" ++
               Numeric.readHex "100000000000000000000!" ++
               Numeric.readOct "10000000000000000000000000!" ++
               Numeric.readBin "100000000000000000000000000000000000000000000000000000000000000000!"
