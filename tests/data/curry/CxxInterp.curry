-- Programs for unit_cxx_interp.py: the ICurry interpreter of the C++
-- runtime runs them, and the values are compared with the compiled code.
module CxxInterp where

import Control.SetFunctions

data Shape = Circle Int | Rect Int Int | Dot
data Pair3 = Pair3 Int Int Int

-- Deterministic recursion with literals and arithmetic.
fact :: Int -> Int
fact n = if n <= 1 then 1 else n * fact (n - 1)

sumList :: [Int] -> Int
sumList []     = 0
sumList (x:xs) = x + sumList xs

-- Nested cases and a nullary constructor as the result.
area :: Shape -> Int
area (Circle r) = 3 * r * r
area (Rect w h) = w * h
area Dot        = 0

classify :: Shape -> Shape
classify s = case s of
  Circle r -> if r == 0 then Dot else Circle r
  Rect w h -> if w == h then Circle w else Rect w h
  Dot      -> Dot

-- Every argument passed on, in another order; a pattern variable read from
-- the matched node.
rot3 :: Int -> Int -> Int -> Pair3
rot3 x y z = Pair3 z x y

firstOf :: Pair3 -> Int
firstOf (Pair3 a _ _) = a

-- A reference result: a primitive, and a constructor.
second :: Int -> Int -> Int
second _ y = y

keepShape :: Int -> Shape -> Shape
keepShape _ s = s

-- Higher-order functions: partial applications with and without arguments,
-- a section, a lambda, a function value applied by apply.
plus :: Int -> Int -> Int
plus a b = a + b

mapPlus :: Int -> [Int] -> [Int]
mapPlus n xs = map (plus n) xs

twice :: (Int -> Int) -> Int -> Int
twice f x = f (f x)

higher :: Int -> [Int]
higher n = [twice (plus 1) n, twice (\x -> x * 2) n, foldr plus 0 [1 .. n]]

compose3 :: Int -> Int
compose3 = (+ 1) . (* 2) . (flip (-) 3)

-- Literals of every kind.
bigInt :: Int
bigInt = 123456789012

chars :: String
chars = ['a', 'z', '\955', '\n']

floats :: Float -> Float
floats x = x * 2.5 + 0.125

greeting :: String
greeting = "hello, world"

-- Cases on literals.
digitName :: Int -> String
digitName 0 = "zero"
digitName 1 = "one"
digitName 2 = "two"
digitName _ = "many"

negName :: Int -> Int
negName (-1) = 10
negName 0    = 20
negName _    = 30

vowel :: Char -> Bool
vowel 'a' = True
vowel 'e' = True
vowel 'i' = True
vowel _   = False

halfOrOne :: Float -> Float
halfOrOne 0.5 = 1.0
halfOrOne 1.0 = 2.0
halfOrOne x   = x

-- Free variables, narrowing, and constraints.
withFree :: Int -> Int
withFree x = y =:= x &> y + 1 where y free

lastOf :: [Int] -> Int
lastOf l | xs ++ [x] =:= l = x where xs, x free

splitFree :: [Int] -> ([Int], [Int])
splitFree l | xs ++ ys =:= l = (xs, ys) where xs, ys free

-- Nondeterminism.
insert :: Int -> [Int] -> [Int]
insert x []     = [x]
insert x (y:ys) = (x : y : ys) ? (y : insert x ys)

perm :: [Int] -> [Int]
perm []     = []
perm (x:xs) = insert x (perm xs)

coin :: Int
coin = 0 ? 1

-- Set functions over nondeterministic functions.
perms :: [Int] -> [[Int]]
perms xs = sortValues (set1 perm xs)

addOne :: Int -> Int
addOne x = x + 1

setPass :: [Int]
setPass = sortValues (set1 addOne (1 ? 2))

hasDup :: [Int] -> Bool
hasDup (_ ++ [x] ++ _ ++ [y] ++ _) | x == y = True

noDup :: [Int] -> Bool
noDup xs = isEmpty (set1 hasDup xs)

-- A recursive let: the first cell refers to the second before it exists.
cyc :: Int -> [Int]
cyc n = let xs = n : ys
            ys = (n + 1) : xs
        in take 5 xs

-- A let that names an argument, and a where with several bindings.
aliasPass :: Int -> (Int, Int)
aliasPass x = let y = x in (y, x)

several :: Int -> Int
several n = a + b + c
  where a = n * 2
        b = a + 1
        c = b * b

-- A failing function (an exempt branch), and failure as a value.
headOf :: [Int] -> Int
headOf (x:_) = x

firstOrZero :: [Int] -> Int
firstOrZero xs = if null xs then 0 else headOf xs

-- An error raised by the program.
boom :: Int -> Int
boom n = if n > 0 then error "boom" else n

-- Monadic code.
ioAdd :: Int -> IO Int
ioAdd n = return (n + 1) >>= \x -> return (x * 2)

-- Strings and characters.
shout :: String -> String
shout s = map toUpper s ++ "!"
  where toUpper c = if c >= 'a' && c <= 'z' then chr (ord c - 32) else c

showAll :: [Int] -> String
showAll xs = show xs ++ show (length xs)

-- A loop of tail calls, for the in-place rewrite.
countDown :: Int -> Int
countDown n = if n == 0 then 0 else countDown (n - 1)

-- A walk by tail calls through a list.
walk :: [Int] -> Int
walk []     = 0
walk (_:xs) = walk xs
