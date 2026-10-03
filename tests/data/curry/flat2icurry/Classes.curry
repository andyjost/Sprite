-- Type classes, instances, derived instances, records, local functions,
-- lambdas, sections, comprehensions, and do notation.
module Classes where

import Sub.Deep

infixl 6 +++
infixr 5 ***

class Container f where
  empty :: f a
  insert :: a -> f a -> f a
  toL :: f a -> [a]
  size :: f a -> Int
  size = length . toL

newtype Stack a = Stack [a]

data Queue a = Queue [a] [a]

instance Container Stack where
  empty = Stack []
  insert x (Stack xs) = Stack (x : xs)
  toL (Stack xs) = xs

instance Container Queue where
  empty = Queue [] []
  insert x (Queue f b) = Queue f (x : b)
  toL (Queue f b) = f ++ reverse b
  size (Queue f b) = length f + length b

data Point = Point { px :: Int, py :: Int, label :: String }
  deriving (Eq, Ord, Show)

data Op = Plus | Minus | Times
  deriving (Eq, Ord, Show, Enum, Bounded)

class Shape a where
  area :: a -> Float
  perimeter :: a -> Float
  describe :: a -> String
  describe x = "area " ++ show (area x) ++ " perimeter " ++ show (perimeter x)

instance Shape Point where
  area _ = 0.0
  perimeter _ = 0.0

(+++) :: [a] -> [a] -> [a]
xs +++ ys = foldr (:) ys xs

(***) :: Int -> Int -> Int
a *** b = a * b + 1

origin :: Point
origin = Point { px = 0, py = 0, label = "origin" }

moveX :: Int -> Point -> Point
moveX d p = p { px = px p + d }

norm1 :: Point -> Int
norm1 (Point { px = x, py = y }) = abs x + abs y

apply :: Op -> Int -> Int -> Int
apply op = case op of
  Plus -> (+)
  Minus -> (-)
  Times -> (*)

allOps :: [Op]
allOps = [minBound .. maxBound]

localFuns :: Int -> Int
localFuns n = go n 0
 where
  go 0 acc = acc
  go k acc = go (k - 1) (acc + step k)
  step k = k * k

lambdas :: [Int] -> [Int]
lambdas xs = map (\x -> x * 2) (filter (\x -> x > 0) xs)

sections :: [Int] -> [Int]
sections xs = map (+ 1) xs ++ map (2 *) xs ++ map (flip (-) 3) xs ++ map (`div` 2) xs

comprehension :: Int -> [(Int, Int)]
comprehension n = [ (x, y) | x <- [1 .. n], y <- [x .. n], x + y == n, odd x ]

asPattern :: Maybe Int -> (Maybe Int, Int)
asPattern m@(Just n) = (m, n)
asPattern m@Nothing = (m, 0)

lazyPattern :: (Int, Int) -> Int
lazyPattern ~(a, b) = a + b

guards :: Int -> String
guards n
  | n < 0 = "negative"
  | n == 0 = "zero"
  | even n = "even"
  | otherwise = "odd"

ifThenElse :: Int -> Int
ifThenElse n = if n > 0 then n else if n < 0 then negate n else 1

doBlock :: IO Int
doBlock = do
  putStrLn "hello"
  x <- return 1
  let y = x + 1
  return (x + y)

maybeDo :: Maybe Int -> Maybe Int
maybeDo m = do
  x <- m
  y <- Just (x + 1)
  return (x * y)

useDeep :: Int -> Int
useDeep n = deep n + unwrapDeep (Deep n)

showDeep :: Deep -> String
showDeep d = show d
