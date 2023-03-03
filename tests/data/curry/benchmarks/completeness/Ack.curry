data Nat = S Nat | O

ack :: Nat -> Nat -> Nat
ack O n = S n
ack (S m) O = ack m (S O)
ack (S m) (S n) = ack m (ack (S m) n)

main :: Nat
main = ack n8 n8
  where n8 = S (S (S (S (S (S (S (S O)))))))
