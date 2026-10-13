-- The programs of unit_setlift.py: the set0 lift of the compiler (decision
-- D28 of 2026-10-12).  The captured variables of the expression of set0
-- are arguments of the capsule, boxed at the entry, as the arguments of
-- setk are: the compiler lifts set0 e over its captured variables x1 .. xk
-- into setk L x1 .. xk, with L x1 .. xk = e a new private function
-- (curry.toolchain.flat2icurry.setlift).  The authority is the paper of
-- Christiansen, Hanus, Reck and Seidel (PPDP 2013, section 3.3):
-- let x = coin in allValues x yields {0} and {1}, one set per outside
-- alternative, and let x = failedBool in allValues x fails instead of
-- yielding a set; the implementations that scope by the time of the first
-- evaluation are not the authority.
--
-- The first part is the parity corpus: each program point set0 e with
-- captured variables stands beside its hand-written lifting setk L xs,
-- and the two give the same values on both backends.  The second part
-- pins the values of the probes of the decision.  The values in the
-- comments are those unit_setlift.py pins.
module SetLift where
import Control.SetFunctions

-- One captured variable: one set per alternative of x.  [1] and [2]
one :: [Int]
one = let x = (0 ? 1) :: Int in sortValues (set0 (x + 1))

oneL :: [Int]
oneL = let x = (0 ? 1) :: Int in sortValues (set1 oneF x)

oneF :: Int -> Int
oneF x = x + 1

-- Two captured variables.  [10], [11], [20] and [21]
two :: [Int]
two = let x = (0 ? 1) :: Int
          y = (10 ? 20) :: Int
      in sortValues (set0 (x + y))

twoL :: [Int]
twoL = let x = (0 ? 1) :: Int
           y = (10 ? 20) :: Int
       in sortValues (set2 twoF x y)

twoF :: Int -> Int -> Int
twoF x y = x + y

-- A class dictionary is a captured variable like any other: show over a
-- Show-constrained parameter captures the dictionary and the parameter,
-- as set1 show x holds the dictionary in the function value.  ["0"] and
-- ["1"]
showD :: Show a => a -> [String]
showD x = sortValues (set0 (show x))

showDL :: Show a => a -> [String]
showDL x = sortValues (set1 show x)

dictS :: [String]
dictS = showD (0 ? 1 :: Int)

dictSL :: [String]
dictSL = showDL (0 ? 1 :: Int)

-- A free variable of the enclosing where is captured: one set per
-- binding, as s6PG of SetFunctionsSemantics.curry (set1 not x where x
-- free).  [False] and [True]
freeS :: [Bool]
freeS = sortValues (set0 (not x)) where x free

freeSL :: [Bool]
freeSL = sortValues (set1 not x) where x free

-- A free variable declared inside the expression is bound there, not
-- captured: the set0 is closed.  [0, 1]
innerFree :: [Int]
innerFree = sortValues (set0 (let x free in (x =:= (0 ? 1)) &> x))

-- Seven captured variables, the largest arity the library has a set
-- function for: set7.  [21] and [22]
seven :: [Int]
seven = sevenP (0 ? 1) 1 2 3 4 5 6

sevenP :: Int -> Int -> Int -> Int -> Int -> Int -> Int -> [Int]
sevenP a b c d e f g = sortValues (set0 (a + b + c + d + e + f + g))

sevenL :: [Int]
sevenL = sevenPL (0 ? 1) 1 2 3 4 5 6

sevenPL :: Int -> Int -> Int -> Int -> Int -> Int -> Int -> [Int]
sevenPL a b c d e f g = sortValues (set7 sevenF a b c d e f g)

sevenF :: Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int
sevenF a b c d e f g = a + b + c + d + e + f + g

-- Nine captured variables, more than the library has set functions for:
-- the lift gives set1 (L x1 .. x8) x9, where the partial application
-- holds eight of them and the runtime boxes those as it boxes the ninth.
-- [36] and [37]
nine :: [Int]
nine = nineP (0 ? 1) 1 2 3 4 5 6 7 8

nineP :: Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> [Int]
nineP a b c d e f g h i = sortValues (set0 (a + b + c + d + e + f + g + h + i))

nineL :: [Int]
nineL = ninePL (0 ? 1) 1 2 3 4 5 6 7 8

ninePL :: Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> [Int]
ninePL a b c d e f g h i = sortValues (set1 (nineF a b c d e f g h) i)

nineF :: Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int -> Int
nineF a b c d e f g h i = a + b + c + d + e + f + g + h + i

-- A nested set0: the inner one is lifted first, and the outer one
-- captures the same variable.  The choice of x escapes both capsules, so
-- the goal has one value per alternative, each the set {2}.  [2] and [2]
nested :: [Int]
nested = let x = (0 ? 1) :: Int
         in sortValues (set0 (length (sortValues (set0 (x ? 5)))))

nestedL :: [Int]
nestedL = let x = (0 ? 1) :: Int in sortValues (set1 nestedF x)

nestedF :: Int -> Int
nestedF x = length (sortValues (set1 nestedG x))

nestedG :: Int -> Int
nestedG x = x ? 5

-- A set0 inside a lambda: the front end lifts the lambda into a function
-- with z as its leading parameter, and the pass lifts the set0 out of
-- that function over y and z.  The choice of z is shared by the two
-- capsules.  [[1], [2]] and [[11], [12]]
lam :: [[Int]]
lam = let z = (0 ? 10) :: Int in map (\y -> sortValues (set0 (y + z))) [1, 2]

lamL :: [[Int]]
lamL = let z = (0 ? 10) :: Int in map (\y -> sortValues (set2 lamF y z)) [1, 2]

lamF :: Int -> Int -> Int
lamF y z = y + z

-- set0 $ e is the call set0 e.  [1] and [2], as one
dollar :: [Int]
dollar = let x = (0 ? 1) :: Int in sortValues (set0 $ x + 1)

dollar2 :: [Int]
dollar2 = let x = (0 ? 1) :: Int in sortValues $ set0 $ x + 1

-- A type annotation at the root of the expression is removed from the
-- body of the lifted function.  [1] and [2], as one
typed :: [Int]
typed = let x = (0 ? 1) :: Int in sortValues (set0 (x + 1 :: Int))

-- set0 in the bodies of a case and under a let binding.  caseS 0: [1];
-- caseS 3: [3] and [4]; letS: [1] and [2]
caseS :: Int -> [Int]
caseS n = case n of
  0 -> sortValues (set0 (n + 1))
  _ -> let y = n ? 2 in sortValues (set0 (y + 1))

caseS0 :: [Int]
caseS0 = caseS 0

caseS3 :: [Int]
caseS3 = caseS 3

letS :: [Int]
letS = let x = (0 ? 1) :: Int
           s = set0 (x + 1)
       in sortValues s

-- The wrapper of the paper: wrap e = set0 e applied to a choice is
-- let e = coin in allValues e, one set per alternative by call-time
-- choice.  [0] and [1]
wrap :: Int -> [Int]
wrap e = sortValues (set0 e)

wrapc :: [Int]
wrapc = wrap (0 ? 1 :: Int)

wrapL :: Int -> [Int]
wrapL e = sortValues (set1 id e)

wrapcL :: [Int]
wrapcL = wrapL (0 ? 1 :: Int)

-- A closed set0 (no captured variable) is unchanged: an encapsulated
-- expression, whose capsule has no box.  [0, 1]
closed :: [Int]
closed = sortValues (set0 (0 ? 1 :: Int))

-- A limit of the lift: set0 as a partial application is no call, so the
-- pass sees no argument.  The element reaches set0 through apply, as an
-- encapsulated expression: one set of both alternatives.  [[0, 1]]
partial :: [[Int]]
partial = map (sortValues . set0) [0 ? 1 :: Int]

-- The probes of decision D28 (2026-10-12), with the values the decision
-- fixes.  Before the lift, heap1 and f0cap gave [] (the failure of the
-- captured variable was the function's own, and the set was empty), and
-- heap2 gave the one set [0, 1].

-- A captured variable that fails: an outside failure of the set function,
-- which fails, as let x = failedBool in allValues x fails in the paper.
-- No value.
heap1 :: [Int]
heap1 = let w = (failed :: Int) in sortValues (set0 (id w)) ++ take 0 [w]

-- A captured choice: one set per alternative.  [0] and [1]
heap2 :: [Int]
heap2 = let x = (0 ? 1) :: Int in sortValues (set0 x)

-- A captured function value that fails.  No value.
f0cap :: [Int]
f0cap = let g = (failed :: Int -> Int) in sortValues (set0 (g 1))

-- Closed expressions that fail: the failure is the function's own, and the
-- set is empty.  [] and []
s0idf :: [Int]
s0idf = sortValues (set0 (id (failed :: Int)))

s0f :: [Int]
s0f = sortValues (set0 (failed :: Int))

-- The failing function value of set1: an outside failure.  No value.
s1f1 :: [Int]
s1f1 = sortValues (set1 (failed :: Int -> Int) 1)

-- A closed choice: one set.  [0, 1]
s0c :: [Int]
s0c = sortValues (set0 (0 ? 1 :: Int))

-- The choice as the argument of set1: one set per alternative.  [0] and [1]
s1idc :: [Int]
s1idc = sortValues (set1 id (0 ? 1 :: Int))
