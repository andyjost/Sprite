absolute :: Int -> Int
absolute x = if x>=0 then x else -x

fac :: Int -> Int
fac n = if n==0 then 1
                else n * fac(n-1)


-- The main expression to be evaluated:
main :: Int
main = fac 10
