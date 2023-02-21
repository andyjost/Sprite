-- n queens: logic solution with permutation and negation-as-failure

-- IDC:
import SearchTree

data Nat = O | S Nat

-- translate integers to nat-terms:
int2nat :: Int -> Nat
int2nat n = if n<=0 then O else S(int2nat (n-1))

nat2int :: Nat -> Int
nat2int O = 0
nat2int (S n) = 1 + nat2int n

mylength :: [_] -> Nat
mylength [] = O
mylength (_:xs) = S (mylength xs)

absdiff :: Nat -> Nat -> Nat -- absdiff x y = abs(x-y)
absdiff O (S x) = S x
absdiff (S x) O = S x
absdiff (S x) (S y) = absdiff x y

permute [] = []
permute (x:xs) = insert (permute xs)
 where insert [] = [x]
       insert (y:ys) = x : y : ys ? y : insert ys

enumTo n = enumFromTo (S O) n -- [1..n] as Peano list
 where
  enumFromTo f n = if n==0 then [] else f : enumFromTo (S f) (n-1)

-- Place n queens on a chessboard so that no queen can capture another queen:
-- (this solution is due to Sergio Antoy)

queens n | y =:= permute (enumTo n) & void (capture y) = y  where y free

capture y = let l1,l2,l3,y1,y2 free in
  l1 ++ [y1] ++ l2 ++ [y2] ++ l3 =:= y & absdiff y1 y2 =:= S (mylength l2)

capt1 = capture [S O, S (S O)] -- success
capt2 = capture [S (S (S O)), S O, S (S (S (S O))), S (S O)] -- fail

void :: Success -> Success
-- PAKCS:
--void c = findall (\_->c) =:= []
-- IDC:
void c = isDefined c =:= False

main = queens 4
