data List = Cons Int List | Nil
concat Nil x = x
concat (Cons a b) x = Cons a (concat b x)

main = concat (Cons 1 Nil) (Cons 2 (Cons 3 Nil))
