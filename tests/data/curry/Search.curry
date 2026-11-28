module Search where
import Control.SetFunctions

data Op = A | B | C | D | E | F
  deriving (Eq, Show)
op :: Op
op = A ? B ? C ? D ? E ? F
run :: Int -> Int -> [Op]
run n acc = if n == 0 then (if acc == 3 then [] else failed)
            else let o = op in o : run (n-1) (if o == A then acc+1 else acc)
main :: [Op]
main = run 7 0
small :: [Op]
small = run 4 0
order :: Int
order = (0 ? 1) ? 2
insert :: a -> [a] -> [a]
insert x ys = (x:ys) ? case ys of
  [] -> failed
  z:zs -> z : insert x zs
perm :: [a] -> [a]
perm [] = []
perm (x:xs) = insert x (perm xs)
permutations :: [Int]
permutations = perm [1,2,3,4,5]
inside :: Int -> Int
inside x = x + (10 ? 20)
capsule :: [Int]
capsule = sortValues (set1 inside (1 ? 2))
nearby :: Int -> Int
nearby x = (x+1) ? (x+2)
suspended :: Int -> [Int]
suspended x = sortValues (set1 nearby x) ? [99]
loop :: Int
loop = loop

-- Observe the nested queue through the order-preserving I/O accessor.
nestedOrder :: IO [Int]
nestedOrder = values2list (set0 order)
sharedChoice :: (Int, Int)
sharedChoice = (let x = 0 ? 1 in (x, x)) ? (2, 2)
failedChoice :: Int
failedChoice = (failed ? failed) ? 2
loops :: Int
loops = loop ? loop
