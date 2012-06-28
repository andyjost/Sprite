-- Carefully selected constants to make sure we actually have
-- enough numbers in the cycle to add a new one each insertion.
m = 39916801
a = 1664525
b = 1013904223
rnd x = (a * x + b) `mod` m

data BT = Leaf | Branch Int BT BT
insert x Leaf = Branch x Leaf Leaf
insert x (Branch y l r) | x < y = Branch y (insert x l) r
                        | y < x = Branch y l (insert x r)
			| x == y = Branch y l r

count Leaf = 0
count (Branch _ l r) = 1 + count l + count r

tree_loop n x t = if n==0 then t
   else tree_loop (n-1) (rnd x) (insert (x`mod`200000) t)

iterations = 200000
someseed = 24642

-- count so it does not print a big tree
main = count (tree_loop iterations someseed Leaf)



