int_arith = ((1 + 2 -3 * 4 `div` 5) `mod` 2) == 1
-- int_cmp | (1<2) && (1<=1) && (1==1) && (1/=2) && (1>=1) && (2>1) = True
--         | True = False

-- char_arith = 'a' == 'b'
-- char_cmp = 'a' < 'b'
main = int_arith
-- main = 1 + 2
-- main = 1 + 2 < 5
-- main = True

