-- graph coloring with non-deterministic functions
-- exploiting the demand-driven search due to lazy evaluation in Curry


-- auxiliary function:

-- negation of ==:
diff x y = (x == y) =:= False

-- This is our actual map:
--
-- -------------------------------------------------
-- |       |        |       |        |       |     |
-- |       |   L2   |       |   L5   |   L9  |     |
-- |       |        |       |        |       |     |
-- |  L1   |--------|  L4   |--------|       |     |
-- |       |        |       |        |-------|     |
-- |       |   L3   |       |   L6   |       |     |
-- |       |        |       |        |   L10 |     |
-- |---------------------------------|       |     |
-- |                    |            |-------|     |
-- |  L7                |     L8     |   L11 |     |
-- |------------------------------------------     |
-- |                     L12                       |
-- -------------------------------------------------
--

data Color = Red | Green | Yellow | Blue deriving Eq
aColor :: Color
aColor = x where x free

-- correct coloring:
correct l1 l2 l3 l4 l5 l6 l7 l8 l9 l10 l11 l12
   | diff l1 l2
   & diff l1 l3
   & diff l1 l7
   & diff l2 l3
   & diff l2 l4
   & diff l3 l4
   & diff l3 l7
   & diff l4 l5
   & diff l4 l6
   & diff l4 l7
   & diff l4 l8
   & diff l5 l6
   & diff l5 l9
   & diff l6 l8
   & diff l6 l9
   & diff l6 l10
   & diff l7 l8
   & diff l7 l12
   & diff l8 l10
   & diff l8 l11
   & diff l8 l12
   & diff l9 l10
   & diff l9 l12
   & diff l10 l11
   & diff l10 l12
   & diff l11 l12
   = [l1,l2,l3,l4,l5,l6,l7,l8,l9,l10,l11,l12]

isList (_:x) = isList x
isList [] = True

-- solution:
main = isList (correct aColor aColor aColor aColor
                       aColor aColor aColor aColor
                       aColor aColor aColor aColor)
