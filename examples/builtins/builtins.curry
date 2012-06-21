int_arith = ((1 + 2 -3 * 4 `div` 5) `mod` 2) == 1
int_cmp  | (1<2) && (1<=1) && (1==1) && (1/=2) && (1>=1) && (2>1) = True
         | True = False
char_cmp | ('a'<'b') && ('a'<='a') && ('a'=='a') && ('a'/='b') && ('a'>='a') && ('b'>'a') = True
         | True = False

main = int_arith && int_cmp && char_cmp

