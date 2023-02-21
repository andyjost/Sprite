-- Benchmark to measure sharing across non-determinism

module ShareNonDet where

data List a = Nil | Cons a (List a)

suCC :: Int -> Int
suCC x = x + 1

isdivs :: Int  -> Int -> Bool
isdivs n x = mod x n /= 0

the_filter :: [Int] -> [Int]
the_filter (n:ns) = myfilter (isdivs n) ns

primes :: [Int]
primes = mymap myhead (myiterate the_filter (myiterate suCC 2))

myfilter :: (Int -> Bool) -> [Int] -> [Int]
myfilter _ []     = []
myfilter p (x:xs) = if p x then x : myfilter p xs
                                else myfilter p xs

myiterate :: (a -> a) -> a -> [a]
myiterate f x = x : myiterate f (f x)

mymap :: (a -> b) -> [a] -> [b]
mymap _ []     = []
mymap f (x:xs) = f x : mymap f xs


myhead :: [Int] -> Int
myhead (x : _) = x

at :: [Int] -> Int -> Int
at (x:xs) n = if n==0  then x 
                       else at xs (n - 1)

insert x ys = x:ys 
insert x ys = insert2 x ys

insert2 x (y:ys) = y:insert x ys

perm []     = []
perm (x:xs) = insert x (perm xs)

sorted :: [Int] -> [Int]
sorted []       = []
sorted [x]      = [x]
sorted (x:y:ys) = guard (x <= y) (x:sorted (y:ys))

psort xs = sorted (perm xs)

guard :: Bool -> [Int] -> [Int]
guard True e = e

myand True y  = y
myand False _ = False

primeList = fromDown 4 0

fromDown n m = if n==m then []
                       else at primes (999+n) : fromDown (n-1) m

goal1 = primeList -- [primes!!1003, primes!!1002, primes!!1001, primes!!1000]

goal2 = psort [7949,7937,7933,7927]

goal3 = psort primeList

main :: [Int]
main = goal1

