-- Programs for unit_py_evaluation.py.  The evaluation of ``check n`` is
-- quadratic in ``n``: ``someNum n`` is a choice among n+1 numbers, and
-- ``x+x`` shares it.
module SomeNum where

someNum :: Int -> Int
someNum n = if (n<=0) then 0 else (n ? someNum (n-1))

isZero :: Int -> Bool
isZero 0 = True

addSomeNum2 :: Int -> Int
addSomeNum2 n = let x = someNum n in x+x

check :: Int -> Bool
check n = isZero (addSomeNum2 n)

main :: Bool
main = check 2000
