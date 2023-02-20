data Nat = O | S Nat
add :: Nat -> Nat -> Nat
add O n = n
add (S n) m = S (add n m)

times :: Nat -> Nat -> Nat
times O _ = O
times (S n) m = add (times n m) m

one = S O
two = S (S O)
three = add one two
four = add two two
five = add two three
six = add three three
seven = add three four

main :: Nat
main = (
    one `times` two `times` three `times` four `times` five `times` six `times` seven
  )

