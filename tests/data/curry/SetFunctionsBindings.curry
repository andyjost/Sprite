-- The programs of unit_setfunctions_bindings.py (issue #97): a set function
-- over a variable that a functional pattern of the enclosing function bound.
module SetFunctionsBindings where
import Control.SetFunctions

-- Section 1: the module of the issue.
g :: String -> Int
g (s ++ ".c") = length s

inner :: String -> [Int]
inner x = sortValues (set1 g x)

-- A nested set function with a literal argument.
h :: String -> Int
h (s ++ ".o") = length s + length (inner "vec.c")

outerLit :: String -> [Int]
outerLit t = sortValues (set1 h t)

-- A nested set function whose argument carries the narrowing of the stem.
k :: String -> Int
k (s ++ ".o") = length (inner (s ++ ".c"))

outerNarrowed :: String -> [Int]
outerNarrowed t = sortValues (set1 k t)

-- The same call outside any set function.
direct :: String -> Int
direct (s ++ ".o") = length (inner (s ++ ".c"))

issue1, issue2, issue3, issue4 :: [Int]
issue1 = inner "vec.c"
issue2 = outerLit "vec.o"
issue3 = outerNarrowed "vec.o"
issue4 = [direct "vec.o"]

-- Section 2: a character the outer pattern bound, compared inside the
-- capsule against a literal.  The capsule must read the binding of the
-- enclosing configuration; bound anew, the character matched the literal.
endsInC :: String -> Int
endsInC (t ++ "c") = length t

outerChar :: String -> [Int]
outerChar (s ++ ".o") = sortValues (set1 endsInC s)

plainChar :: String -> Int
plainChar (s ++ ".o") = endsInC s

charMatch, charMismatch :: [Int]
charMatch = outerChar "xc.o"
charMismatch = outerChar "cx.o"

charPlainMatch, charPlainMismatch :: Int
charPlainMatch = plainChar "xc.o"
charPlainMismatch = plainChar "cx.o"

-- The same with an Int field and a list tail that the outer pattern bound.
endsIn5 :: [Int] -> Int
endsIn5 (ys ++ [5]) = length ys

outerInt :: [Int] -> [Int]
outerInt (id (x : xs)) = sortValues (set1 endsIn5 (x : xs))

intMatch, intMismatch :: [Int]
intMatch = outerInt [3, 5]
intMismatch = outerInt [5, 3]

-- Section 3: a list the outer pattern bound non-strictly (xs =:<= arg,
-- through id), whose structure the capsule narrows.  The capsule narrowed
-- the shared variable, and the enclosing configuration then met the
-- generator of a variable it had bound: the binding was applied at every
-- fork, without end.
endsIn0 :: [Int] -> Int
endsIn0 (ys ++ [0]) = length ys

outerList :: [Int] -> [Int]
outerList (id xs) = sortValues (set1 endsIn0 xs)

outerTail :: [Int] -> [Int]
outerTail (id (x : xs)) = sortValues (set1 endsIn0 xs)

listWhole, listTail :: [Int]
listWhole = outerList [1, 2, 0]
listTail = outerTail [1, 2, 0]

-- Section 4: no set function.  One alternative binds x with =:<= and reads
-- it; another narrows x.  The first then meets the generator of a variable
-- it bound.
len0 :: [Int] -> Int
len0 [] = 0
len0 (_ : _) = 1

sibling :: Int
sibling = (x =:<= [1, 2] &> (length x ? 7)) ? len0 x
  where x free

-- Section 5: a bound character read by a case or a comparison inside the
-- capsule.  The private shapes bind c before the capsule starts, so the
-- capsule reads the binding of the enclosing configuration; both goals
-- suspended before the fix.  The shared shapes start the capsule while c
-- is free: select takes the first value as the capsule makes it, the
-- enclosing configuration then forks and binds c to 'a' and to 'b', and
-- each alternative takes the second value from the same capsule.  The
-- first configuration to run the capsule puts its binding into the nested
-- spine, and the other reads a value made with that binding: both give
-- (0, 1) where the plain goals give (0, 1) and (0, 2).  Both shared goals
-- suspended before the fix.  The functional-pattern shape is the same with
-- a string: the plain goal gives (0, 1) alone, the shared shape gives it
-- twice.  The item is the owner's (the TODO entry of 2026-10-07).
gCase :: Char -> Int
gCase c = 0 ? hCase c

hCase :: Char -> Int
hCase c = case c of
  'a' -> 1
  'b' -> 2

gEq :: Char -> Int
gEq c = 0 ? hEq c

hEq :: Char -> Int
hEq c = if c == 'a' then 1 else 2

gPat :: String -> Int
gPat s = 0 ? endsInA s

endsInA :: String -> Int
endsInA (t ++ "a") = length t

plainCase, plainEq, plainPat :: (Int, Int)
plainCase = (c =:<= 'a' ? c =:<= 'b') &> (0, hCase c) where c free
plainEq = (c =:<= 'a' ? c =:<= 'b') &> (0, hEq c) where c free
plainPat = (s =:<= "xa" ? s =:<= "xb") &> (0, endsInA s) where s free

privateCase, privateEq :: (Int, Int)
privateCase = (c =:<= 'a' ? c =:<= 'b') &> twoValues (set1 gCase c) where c free
privateEq = (c =:<= 'a' ? c =:<= 'b') &> twoValues (set1 gEq c) where c free

-- The two values of a set, sorted.
twoValues :: Values Int -> (Int, Int)
twoValues s = let vs = sortValues s in (head vs, vs !! 1)

sharedCase, sharedEq, sharedPat :: (Int, Int)
sharedCase = let (first, rest) = select (set1 gCase c)
             in (first, (c =:<= 'a' ? c =:<= 'b') &> selectValue rest)
  where c free
sharedEq = let (first, rest) = select (set1 gEq c)
           in (first, (c =:<= 'a' ? c =:<= 'b') &> selectValue rest)
  where c free
sharedPat = let (first, rest) = select (set1 gPat s)
            in (first, (s =:<= "xa" ? s =:<= "xb") &> selectValue rest)
  where s free
