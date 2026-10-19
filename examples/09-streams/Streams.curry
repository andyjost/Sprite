module Streams where

import Sprite.Stream (yield)

threeOut :: IO ()
threeOut = mapM_ yield [1, 2, 3 :: Int]

primes :: [Int]
primes = sieve [2..]
  where sieve (x:xs) = x : sieve (filter (\y -> y `mod` x > 0) xs)

primesOut :: IO ()
primesOut = mapM_ yield primes

-- Thread the running state through the action, rather than through Python.
totalsOut :: IO Int
totalsOut = totals 0 [1, 2, 3]
  where totals n [] = return n
        totals n (x:xs) = do
          yield (n + x)
          totals (n + x) xs
