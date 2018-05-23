data Nat = O | S Nat
add O n = n
add (S n) m = S (add n m)
