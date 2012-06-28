-- Carefully selected constants to make sure we actually have
-- enough numbers in the cycle to add a new one each insertion.
m = 39916801
a = 1664525
b = 1013904223
rnd x = (a * x + b) `mod` m

-- user defined list

data List a = Nil | Cons a (List a)
mylength Nil = 0
mylength (Cons _ y) = 1 + mylength y

insert x Nil = Cons x Nil
insert x (w @ (Cons y z)) | x > y = Cons y (insert x z)
               | x == y = w
               | True = Cons x w

loop n x t = if n==0 then t
   else loop (n-1) (rnd x) (insert (x`mod`200000) t)

iterations = 10000
someseed = 24642

-- length so it does not print a long list
main = mylength (loop iterations someseed Nil)




