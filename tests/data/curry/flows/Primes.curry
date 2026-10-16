-- A25's example over the primes of inflists (PAKCS examples, BSD license).
module Primes where

import Sprite.Stream

from :: Int -> [Int]
from n = n : from (n+1)

primes :: [Int]
primes = sieve (from 2)

sieve :: [Int] -> [Int]
sieve (x:xs) = x : sieve (filter (\y -> y `mod` x > 0) xs)

primesOut :: IO ()
primesOut = mapM_ yield primes

threeOut :: IO ()
threeOut = mapM_ yield [1, 2, 3 :: Int]

strOut :: IO ()
strOut = mapM_ yield "ab"

ndOut :: IO ()
ndOut = yield (1 ? 2 :: Int)
