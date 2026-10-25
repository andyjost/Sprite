data BinTree a = Leaf | Branch a (BinTree a) (BinTree a)

findCurry :: BinTree String -> Bool
findCurry Leaf           = False
findCurry (Branch x l r) = x == "Curry" || findCurry l || findCurry r

type IntTree = BinTree Int

total :: IntTree -> Int
total Leaf           = 0
total (Branch x l r) = x + total l + total r

sample1 :: BinTree String
sample1 = Branch "is" (Branch "Curry" Leaf Leaf) (Branch "good" Leaf Leaf)

sample2 :: IntTree
sample2 = Branch 7 (Branch 5 Leaf Leaf) (Branch 9 Leaf Leaf)

-- tests:
main :: Int
-- main = findCurry sample1
main = total sample2
