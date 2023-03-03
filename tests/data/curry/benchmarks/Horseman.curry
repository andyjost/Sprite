-- HORSEMAN: relation between men, horses and their heads and feet:

data Nat = O | S Nat

-- translate integers to nat-terms:
int2nat :: Int -> Nat
int2nat n = if n<=0 then O else S(int2nat (n-1))


-- addition on naturals:
add O     n = n
add (S m) n = S (add m n)


horseman m h heads feet =
   heads =:= add m h  &  feet =:= add (add m m) (add (add h h) (add h h))


-- How many men and horses have 460 heads and 1160 feet?
goal4 m h = horseman m h (int2nat 460) (int2nat 1160)
main4 = goal4 m h &> (m, h) where m,h free

main = main4
