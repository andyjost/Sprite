-- Recursive and mutually recursive lets, which need INodeAssign fix-ups, and
-- lets in nested positions, which are lifted to _LET functions.
module Lets where

ones :: [Int]
ones = let xs = 1 : xs in xs

twos :: [Int]
twos = let xs = 2 : ys
           ys = 2 : xs
        in xs

deepCycle :: [Int]
deepCycle = let xs = map (+ 1) (0 : xs) in xs

orCycle :: [Int]
orCycle = let xs = (1 : xs) ? (2 : xs) in xs

threeWay :: ([Int], [Int], [Int])
threeWay = let as = 1 : bs
               bs = 2 : cs
               cs = 3 : as
            in (as, bs, cs)

selfInTuple :: (Int, [Int])
selfInTuple = let p = (1, snd p) in p

nestedLet :: Int -> Int
nestedLet n = let a = n + 1 in let b = a * 2 in a + b

letInBranch :: Maybe Int -> Int
letInBranch m = case m of
  Nothing -> 0
  Just n -> let k = n * n in k + k

letInArg :: Int -> Int
letInArg n = succ (let k = n + 1 in k * k)

letWithCase :: Int -> Int
letWithCase n = let k = case n of
                          0 -> 1
                          _ -> n
                 in k + 1

freeInLet :: Int -> [Int]
freeInLet n = let xs = x : [n] in xs
 where x free

typedLet :: Int -> Int
typedLet n = let k = (n :: Int) in (k + 1 :: Int)

letSharing :: Int -> (Int, Int)
letSharing n = (a, a)
 where a = n * n
