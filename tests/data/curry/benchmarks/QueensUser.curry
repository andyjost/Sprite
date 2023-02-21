-- Compute the number of solutions to queens placements
-- Uses user-defined lists and functions.

data List a = Nil | Cons a (List a)

nsoln :: Int -> Int
nsoln x1 = mylength (gen x1 x1)

safe :: Int -> Int -> List Int -> Bool
safe _ _ Nil = True
safe x1 x2 (Cons x4 x5) =
     (x1 /= x4) &&&
     ((x1 /= (x4 + x2)) &&&
     ((x1 /= (x4 - x2)) &&& (safe x1 (x2 + 1) x5)))

gen :: Int -> Int -> List (List Int)
gen x1 x2
 = case x2 == 0 of
    True -> Cons Nil Nil
    False -> myconcatMap (gen'' x1) (gen x1 (x2 - 1))

gen'' :: Int -> List Int -> List (List Int)
gen'' x1 x2
 = myconcatMap (gen' x2) (myenumFromTo 1 x1)

gen' :: List Int -> Int -> List (List Int)
gen' x1 x2
 = case safe x2 1 x1 of
    True -> Cons (Cons x2 x1) Nil
    False -> Nil

myconcatMap :: (a -> List b) -> List a -> List b
myconcatMap f = punkt myconcat (mymap f)

mymap :: (a -> b) -> List a -> List b
mymap _ Nil         = Nil
mymap f (Cons x xs) = Cons (f x) (mymap f xs)

myconcat :: List (List a) -> List a
myconcat l = myfoldr app Nil l

myfoldr :: (List a -> List a -> List a) -> List a -> List (List a) -> List a
myfoldr _ e Nil = e
myfoldr f e (Cons x xs) = f x (myfoldr f e xs)

myenumFromTo n m = if n>m then Nil else Cons n (myenumFromTo (n+1) m)

punkt :: (b -> c) -> (a -> b) -> a -> c
punkt f g x = f (g x)

app Nil ys = ys
app (Cons x xs) ys = Cons x (app xs ys)

mylength          :: List _ -> Int
mylength Nil       = 0
mylength (Cons _ xs)   = 1 + mylength xs

(&&&)            :: Bool -> Bool -> Bool
True  &&& x      = x
False &&& _      = False



goal0 = nsoln 10
goal1 = nsoln 11

main = goal0 -- AJ goal1
