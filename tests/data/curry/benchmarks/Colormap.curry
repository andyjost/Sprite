-- constraint solving (simple generate and test) in Curry:
-- graph coloring


-- auxiliary function:

-- negation of ==:
diff :: Eq a => a -> a -> Bool
diff x y = (x == y) =:= False

{-
 This is our actual map:

 --------------------------
 |       |        |       |
 |       |   L2   |       |
 |       |        |       |
 |  L1   |--------|  L4   |
 |       |        |       |
 |       |   L3   |       |
 |       |        |       |
 --------------------------
-}

data Color = Red | Green | Yellow | Blue deriving Eq


isColor :: Color -> Bool
isColor Red    = success
isColor Yellow = success
isColor Green  = success
isColor Blue   = success


coloring :: Color -> Color -> Color -> Color -> Bool
coloring l1 l2 l3 l4 = isColor l1 & isColor l2 & isColor l3 & isColor l4


-- correct coloring:
correct :: Color -> Color -> Color -> Color -> Bool
correct l1 l2 l3 l4
   = diff l1 l2 & diff l1 l3 & diff l2 l3 & diff l2 l4 & diff l3 l4


-- generate+test solution:
goal1 l1 l2 l3 l4 = coloring l1 l2 l3 l4 & correct l1 l2 l3 l4
main1 = goal1 a b c d &> (a,b,c,d) where a,b,c,d free


-- test+generate solution:
goal2 l1 l2 l3 l4 = correct l1 l2 l3 l4 & coloring l1 l2 l3 l4
main2 = goal2 a b c d &> (a,b,c,d) where a,b,c,d free


main = (main1, main2)
