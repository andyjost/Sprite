-- Weak encapsulation probes. Lists are sorted observations of value sets.
-- Directives give top-level answers, independent of evaluation order.
-- Reference: dissertation chapter 2, equation 2.1 (pp. 73-74).
-- Failure is a node; nothing is decided until that node is demanded.
module Probes where
import Control.Search.SetFunctions

data Bit = A | B deriving (Eq, Ord, Show)

const1 :: Int -> Int
const1 _ = 1

dbl :: Int -> Int
dbl x = x + x

never :: Int -> Int
never _ = failed

-- Value unusedFailure: ["[1]"]
-- The failure basis element suffices: const1 never demands its argument.
unusedFailure :: [Int]
unusedFailure = sortValues (set1 const1 (head []))

-- Value neededFailure: []
-- id demands the failed argument; no basis element yields a value.
neededFailure :: [Int]
neededFailure = sortValues (set1 id (head [] :: Int))

-- Value outsideChoice: ["[2]", "[4]"]
-- Each argument basis element has its own singleton, not one set {2,4}.
outsideChoice :: [Int]
outsideChoice = sortValues (set1 dbl (1 ? 2))

-- Value sharedChoice: ["(1,[2])", "(2,[4])"]
-- Both occurrences denote the same choice; cross pairs are impossible.
sharedChoice :: (Int, [Int])
sharedChoice = (x, sortValues (set1 dbl x)) where x = 1 ? 2

data Route = Short | Long deriving (Eq, Ord, Show)
route :: Route
route = Short ? Long
flight :: (Route, Int)
flight = (Short, 1) ? (Long, 2)
duration :: Route -> Int
duration r | flight =:= (r,n) = n where n free
shorter :: Int -> Route
shorter limit | duration candidate < limit = candidate where candidate = route

-- Value sharedLookup: ["Short"]
-- Issue #171: at duration 1 there is no shorter route; at 2 there is Short.
-- Failed lookup branches cannot invent an empty set for the Long branch.
sharedLookup :: Route
sharedLookup | isEmpty (set1 shorter (duration result)) = result
  where result = route

-- Value mixedFailure: []
-- D45: the only argument basis element is failure. Both function branches
-- fail there; their empty value set has the value of failure (eq. 2.1).
mixedFailure :: Bool
mixedFailure = isEmpty (set1 (\a -> (a + 1) ? failed) (failed :: Int))

-- Value mixedFailureReversed: []
-- The same basis calculation must hold with the branches reversed.
mixedFailureReversed :: Bool
mixedFailureReversed = isEmpty (set1 (\a -> failed ? (a + 1)) (failed :: Int))

-- Value mixedValue: ["[2]"]
-- The function's 2 survives both failed branches; failure adds no value.
mixedValue :: [Int]
mixedValue = sortValues (set1 (\a -> (a + 1) ? (failed ? 2)) failed)

inner :: Int -> [Int]
inner n = sortValues (set1 dbl n)
nested :: Int -> [Int]
nested n = sortValues (set1 (\x -> x ? x + 1) n)

-- Value nestedIndependent: ["[[2,3]]"]
-- Inner choices belong to the inner set; outer encapsulation sees a list.
nestedIndependent :: [[Int]]
nestedIndependent = sortValues (set1 nested 2)

-- Value nestedShared: ["(1,[[2]])", "(2,[[4]])"]
-- The shared argument's choice escapes both capsules and stays correlated.
nestedShared :: (Int, [[Int]])
nestedShared = (x, sortValues (set1 inner x)) where x = 1 ? 2

-- Value nestedUnusedFailure: ["[[1]]"]
-- Neither capsule needs the failed argument: the inner constant yields 1.
nestedUnusedFailure :: [[Int]]
nestedUnusedFailure = sortValues (set1 (\a -> sortValues (set1 const1 a)) failed)

-- Value narrowedBefore: ["(A,[A])", "(B,[B])"]
-- The outside constraint chooses a basis element before the capsule starts.
narrowedBefore :: (Bit, [Bit])
narrowedBefore = (x =:= (A ? B)) &> (x, sortValues (set1 id x)) where x free

first :: Bit -> Bit
first x = A ? x
finish :: [Bit] -> Bit -> [Bit]
finish xs x | x =:= (A ? B) = xs

-- Value narrowedAfter: ["[A,A]", "[A,B]"]
-- isEmpty starts the capsule with its constant A; the outside then binds x.
-- The resumed capsule must take that binding, never a sibling's binding.
narrowedAfter :: [Bit]
narrowedAfter = let s = set1 first x
               in if isEmpty s then [] else finish (sortValues s) x
  where x free

bindA :: Bit -> Bool
bindA x = (x =:= A) &> True

-- Value bindingEscape: ["(A,[True])", "(B,[])"]
-- D54: D48's wider escape condition gives both bases; follows D48 if revised.
bindingEscape :: (Bit, [Bool])
bindingEscape = let xs = sortValues (set1 bindA x)
                in if null xs then (x,[]) else (x,xs)
  where x free

select :: Bit -> Int
select A = 7
select B = failed

-- Value insideAfterOutside: ["(A,[7])", "(B,[])"]
-- D54: total outside B fails only inside, yielding an observable empty set.
insideAfterOutside :: (Bit, [Int])
insideAfterOutside = (x, sortValues (set1 select x)) where x = A ? B

-- Value emptyIsEmpty: ["True"]
-- D54: without outside failure, D45 leaves the empty capsule observable.
emptyIsEmpty :: Bool
emptyIsEmpty = isEmpty (set1 never 0)

-- Value emptyNotEmpty: ["False"]
-- D54: without outside failure, the observable empty set is not nonempty.
emptyNotEmpty :: Bool
emptyNotEmpty = notEmpty (set1 never 0)

naturals :: Int -> Int
naturals n = n ? naturals (n + 1)

-- Value infiniteIsEmpty: ["False"]
-- A first value witnesses nonemptiness; no enumeration of the infinite set.
infiniteIsEmpty :: Bool
infiniteIsEmpty = isEmpty (set1 naturals 0)

-- CHRS13 adaptations below use setN in place of the paper's allValues.
inc12 :: Int -> Int
inc12 n = (n + 1) ? (n + 2)
coin :: Int
coin = 0 ? 1
coinList :: [Int]
coinList = [coin]
nilP :: [Int] -> Bool
nilP [] = True
nilP (_:_) = failed

-- Value chrsInc12: ["[2,3]", "[6,7]"]
-- CHRS13 section 3: inc12S; internal choices grouped per outside argument.
chrsInc12 :: [Int]
chrsInc12 = sortValues (set1 inc12 (1 ? 5))

-- Value chrsAllCoins: ["[0]", "[1]"]
-- CHRS13 section 3.2: allCoins, weak rather than strong encapsulation.
chrsAllCoins :: [Int]
chrsAllCoins = sortValues (set1 id coin)

-- Value chrsNumCoinLists: ["2"]
-- CHRS13 section 3.1: numCoinLists, normal form rather than head normal form.
chrsNumCoinLists :: Int
chrsNumCoinLists = length (sortValues (set0 coinList))

-- Value chrsOutsideFailure: []
-- CHRS13 section 3.4: consP(fl), demanded outside failure is not negated.
chrsOutsideFailure :: Bool
chrsOutsideFailure = isEmpty (set1 nilP (failed :: [Int]))

-- Value chrsFailureChoice: ["[True]"]
-- CHRS13 section 3.4: let x = failed in allValues(x ? True).
-- The independent True survives; demanding the other branch fails only it.
chrsFailureChoice :: [Bool]
chrsFailureChoice = sortValues (set1 (\x -> x ? True) failed)

-- Value chrsFailureChoiceReversed: ["[True]"]
-- The same example with the branches swapped, to expose scheduling effects.
chrsFailureChoiceReversed :: [Bool]
chrsFailureChoiceReversed = sortValues (set1 (\x -> True ? x) failed)
