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
-- suspended before the fix of #97.  The shared shapes start the capsule
-- while c is free: select takes the first value as the capsule makes it,
-- the enclosing configuration then forks and binds c to 'a' and to 'b',
-- and each alternative takes the second value from the same capsule.
-- Before the rule for a shared capsule (section 6) the first configuration
-- to run the capsule put its binding into the nested spine, and the other
-- read a value made with that binding: both gave (0, 1) where the plain
-- goals give (0, 1) and (0, 2).  The functional-pattern shape is the same
-- with a string: the plain goal gives (0, 1) alone, and the shared shape
-- gave it twice.
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

-- Section 6: the rule for a shared capsule (decision D3 of the memo on the
-- Fair Scheme proofs, route (c); issue #86).  A capsule whose evaluation
-- reads a binding of the configuration that runs it is cloned for that
-- configuration at the first such read, and the clone absorbs the binding;
-- so two alternatives that bound a variable of the capsule's goal after it
-- started each compute their own set, as the plain goals do.  Every capsule
-- below starts while its variable is free and gives its first value before
-- the alternatives bind the variable.

-- The binding made by =:=, a value binding of a character.
sharedStrict :: (Int, Int)
sharedStrict = let (first, rest) = select (set1 gCase c)
               in (first, (c =:= 'a' ? c =:= 'b') &> selectValue rest)
  where c free

plainStrict :: (Int, Int)
plainStrict = (c =:= 'a' ? c =:= 'b') &> (0, hCase c) where c free

-- A variable of a data type narrowed after the start.  Its generator
-- escapes the capsule (the repair of issue #61); no binding is read.
data AB = A | B

gAB :: AB -> Int
gAB t = 0 ? hAB t

hAB :: AB -> Int
hAB A = 1
hAB B = 2

sharedNarrow :: (Int, Int)
sharedNarrow = let (first, rest) = select (set1 gAB t)
               in (first, (t =:= A ? t =:= B) &> selectValue rest)
  where t free

plainNarrow :: (Int, Int)
plainNarrow = (t =:= A ? t =:= B) &> (0, hAB t) where t free

-- A functional pattern binds the variable after the start: the match of
-- id "xa" against the free s narrows the spine of s and binds its
-- characters.  seq forces the match before the capsule is read again.
isXA, isXB :: String -> Int
isXA (id "xa") = 1
isXB (id "xb") = 2

sharedFunPat :: (Int, Int)
sharedFunPat = let (first, rest) = select (set1 gPat s)
                   n = isXA s ? isXB s
               in n `seq` (first, n + selectValue rest)
  where s free

plainFunPat :: (Int, Int)
plainFunPat = let n = isXA s ? isXB s in n `seq` (0, n + endsInA s)
  where s free

-- Nested capsules: the inner set function reads the variable of the outer
-- one, bound after both started.  The outer capsule is cloned first, for
-- the alternative, and the inner one next, for the clone's configuration.
gNested :: Char -> Int
gNested c = 0 ? head (sortValues (set1 hCase c))

sharedNested :: (Int, Int)
sharedNested = let (first, rest) = select (set1 gNested c)
               in (first, (c =:<= 'a' ? c =:<= 'b') &> selectValue rest)
  where c free

-- Two variables bound after the start: the clone of the first read
-- diverges again at the second.
gTwo :: Char -> Char -> Int
gTwo c d = 0 ? (hCase c * 10 + hCase d)

sharedTwo :: (Int, Int)
sharedTwo = let (first, rest) = select (set2 gTwo c d)
            in (first, (c =:<= 'a' ? c =:<= 'b')
                  &> ((d =:<= 'a' ? d =:<= 'b') &> selectValue rest))
  where c, d free

plainTwo :: (Int, Int)
plainTwo = (c =:<= 'a' ? c =:<= 'b')
  &> ((d =:<= 'a' ? d =:<= 'b') &> (0, hCase c * 10 + hCase d))
  where c, d free

-- One alternative alone binds the variable after the start: no clone, the
-- capsule absorbs the binding in place.
soleReader :: (Int, Int)
soleReader = let (first, rest) = select (set1 gCase c)
             in (first, (c =:<= 'a') &> selectValue rest)
  where c free

-- The binding predates the capsule, and the alternative that made it forks
-- later on something else.  Every alternative holds the binding, so a read
-- of it is no divergence: the capsule absorbs the binding at its creation,
-- and no clone is made.
boundThenFork :: Int
boundThenFork = (c =:<= 'a') &>
    (let (first, rest) = select (set1 gCase c)
     in first `seq` (selectValue rest ? (selectValue rest + 10)))
  where c free

plainBoundThenFork :: Int
plainBoundThenFork = (c =:<= 'a') &> (hCase c ? (hCase c + 10)) where c free

-- One alternative reads the shared capsule through two references.  Each
-- reference clones the capsule at its first read, since the clone goes into
-- a private copy of the spine of that reference alone, and the shared node
-- stays for the other.  The values are right; the nested work after the
-- clone point is done per clone (the owner's item in the TODO entry of
-- 2026-10-09).
twoRefs :: (Int, Int)
twoRefs = let (first, rest) = select (set1 gCase c)
          in (first, (c =:<= 'a' ? c =:<= 'b')
                &> (selectValue rest * 10 + selectValue rest))
  where c free

plainTwoRefs :: (Int, Int)
plainTwoRefs = (c =:<= 'a' ? c =:<= 'b') &> (0, hCase c * 10 + hCase c)
  where c free
