-- External declarations in a user module (IExternal), operator declarations,
-- data types with a type synonym between them, and functions whose bodies
-- are a single call of Prelude.failed.
module Externals where

infixl 7 <+>

data T1 = T1a | T1b
type Syn = [T1]
data T2 = T2a Syn | T2b T1
type Syn2 = T2
data T3 = T3 Syn2 Syn

prim_ext :: Int -> Int
prim_ext external

ext2 :: Int -> Int -> Int
ext2 external

(<+>) :: Int -> Int -> Int
a <+> b = a + b + ext2 a b

alwaysFails :: Int
alwaysFails = failed

failsInArg :: Int -> Int
failsInArg n = n + failed

failsInBranch :: T1 -> Int
failsInBranch t = case t of
  T1a -> failed
  T1b -> 1

failsPartial :: [Int] -> [Int]
failsPartial = map (const failed)

useT3 :: T3 -> Int
useT3 (T3 (T2a ts) ts2) = length ts + length ts2
useT3 (T3 (T2b _) _) = 0

typedFailed :: Int
typedFailed = (failed :: Int)

typedCall :: Int -> Int
typedCall n = (succ n :: Int)
