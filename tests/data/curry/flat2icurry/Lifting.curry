-- Shapes that drive the lifting pass: nested cases, complex scrutinees with
-- their own nested work, free variables and lets in branches, typed
-- expressions, and a name that collides with a generated one.
module Lifting where

data Color = Red | Green | Blue
  deriving (Eq, Ord, Show)

data Tree = Leaf | Node Tree Int Tree
  deriving (Eq, Show)

nested :: Maybe (Maybe Int) -> Int
nested m = succ (case m of
  Nothing -> 0
  Just n -> case n of
    Nothing -> 1
    Just k -> k)

complexScrutinee :: [Int] -> Int
complexScrutinee xs = case map succ (case xs of
                                        [] -> [0]
                                        (y:ys) -> y : ys) of
  [] -> 0
  (z:_) -> case z of
    0 -> 1
    _ -> z

complexLit :: Int -> Int
complexLit n = case n + 1 of
  0 -> 1
  1 -> 2
  _ -> case n * 2 of
    4 -> 5
    _ -> 6

freeInBranch :: Maybe Int -> [Int]
freeInBranch m = case m of
  Nothing -> let x free in [x]
  Just n -> let y, z free in y =:= n &> [y, z]

freeAtRoot :: Int -> [Int]
freeAtRoot n = let x, y free in x =:= n &> [x, y]

freeInArg :: Int -> Int
freeInArg n = succ (let x free in x =:= n &> x)

typedRoot :: Int -> Int
typedRoot n = (case n of
  0 -> 1
  _ -> 2) :: Int

typedArg :: Int -> Int
typedArg n = succ ((case n of
  0 -> 1
  _ -> n) :: Int)

typedOr :: Int -> Int
typedOr n = (n :: Int) ? (succ n :: Int)

collide :: Bool -> Int
collide b = succ (case b of
  True -> 1
  False -> 2)

collide_CASE0 :: Int
collide_CASE0 = 42

collide_CASE1 :: Int
collide_CASE1 = 43

twice :: Bool -> Bool -> Int
twice a b = succ (case a of
  True -> 1
  False -> 2) + succ (case b of
  True -> 10
  False -> 20)

twice_CASE1 :: Int
twice_CASE1 = 0

orBranches :: Color -> Int
orBranches c = (case c of
  Red -> 1
  Green -> 2
  Blue -> 3) ? (case c of
  Blue -> 30
  _ -> 0)

incomplete :: Color -> Int
incomplete c = case c of
  Blue -> 3
  Red -> 1

incompleteTree :: Tree -> Int
incompleteTree t = case t of
  Node _ n _ -> n

reordered :: Tree -> Int
reordered t = case t of
  Node l n r -> n + reordered l + reordered r
  Leaf -> 0

insert :: Int -> Tree -> Tree
insert x t = case t of
  Leaf -> Node Leaf x Leaf
  Node l n r | x < n -> Node (insert x l) n r
             | x > n -> Node l n (insert x r)
             | otherwise -> t

caseInLet :: Int -> Int
caseInLet n = let k = case n of
                        0 -> 1
                        _ -> 2
                  j = k + 1
               in case k of
                    1 -> j
                    _ -> n

caseInFree :: Int -> Int
caseInFree n = let x free in case x =:= n of
  True -> x

letThenCase :: Maybe Int -> Int
letThenCase m = let k = 1 in case m of
  Nothing -> k
  Just n -> n + k

manyVars :: [Int] -> Maybe Int -> Int
manyVars [a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13,a14,a15,a16,a17,a18,a19,a20
         ,a21,a22,a23,a24,a25,a26,a27,a28,a29,a30,a31,a32,a33,a34,a35,a36,a37,a38,a39,a40
         ,a41,a42,a43,a44,a45,a46,a47,a48,a49,a50,a51,a52,a53,a54,a55,a56,a57,a58,a59,a60
         ,a61,a62,a63,a64,a65,a66,a67,a68,a69,a70,a71,a72,a73,a74,a75,a76,a77,a78,a79,a80
         ,a81,a82,a83,a84,a85,a86,a87,a88,a89,a90,a91,a92,a93,a94,a95,a96,a97,a98,a99,a100
         ,a101,a102,a103,a104,a105] m =
  a1 + a50 + a105 + (case m of
                       Just n -> n + a104)
