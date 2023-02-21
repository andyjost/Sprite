data Nat = Z | S Nat

nat2int :: Nat -> Int
nat2int Z     = 0
nat2int (S n) = 1 + nat2int n

int2nat :: Int -> Nat
int2nat n = if n <= 0 then Z else S (int2nat (n-1))

plus :: Nat -> Nat -> Nat
plus Z     m = m
plus (S n) m = S (plus n m)

sumNat :: [Nat] -> Nat
sumNat = foldr plus Z

-- Eingabe: #Köpfe, #Füße
-- Ausgabe: (#Menschen, #Pferde)
horseman :: Int -> Int -> (Int, Int)
horseman heads feet | int2nat heads =:= m `plus` h
                    & int2nat feet  =:= sumNat [m,m,h,h,h,h]
                    = (nat2int m, nat2int h)
  where m, h free

main = horseman 460 1160