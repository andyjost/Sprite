-- Partial applications of constructors (ICPCall) and of functions with no
-- arguments, and the choice operator in saturated and unsaturated forms.
module Partials where

data Pair a b = Pair a b

data Three = A | B Int | C Int Int

justs :: [Int] -> [Maybe Int]
justs = map Just

pairs :: [Int] -> [Pair Int Int]
pairs = map (Pair 1)

pairsFlip :: [Int] -> [Pair Int Int]
pairsFlip = map (flip Pair 1)

conses :: [Int] -> [Int]
conses = foldr (:) []

tuples :: [Int] -> [(Int, Int)]
tuples = zipWith (,) [0 ..]

cs :: [Int] -> [Int -> Three]
cs = map C

bs :: [Int -> Three]
bs = [B, B]

compose :: (Int -> Int) -> Int -> Int
compose = (.) succ

noArgs :: [Int] -> [Int]
noArgs = map succ

choose :: Int -> Int -> Int
choose x y = x ? y

chooseUnsat :: Int -> Int -> Int
chooseUnsat x = (?) x

chooseSection :: Int -> Int
chooseSection = (1 ?)

chooseApply :: Int -> Int -> Int -> Int
chooseApply f x y = (?) x y `seq` f

applyMany :: (Int -> Int -> Int -> Int) -> Int
applyMany f = f 1 2 3

applyPartial :: Int -> Int -> Int -> Int
applyPartial = applyThree

applyThree :: Int -> Int -> Int -> Int
applyThree a b c = a + b + c

eta :: [Int] -> [Int]
eta xs = map (applyThree 1 2) xs
