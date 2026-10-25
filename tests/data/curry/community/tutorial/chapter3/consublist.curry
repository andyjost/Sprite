-- Compute a sublist l of the integer argument list with the constraint
-- that the last element of l is twice the first.
-- E.g., the expected results of the test data are [3,6] and [2,1,4]

consublist :: [Int] -> [Int]
consublist (_++[x]++y++[z]++_) | 2*x == z = [x]++y++[z]

testdata :: [Int]
testdata = [3,6,2,1,4,5]

main :: [Int]
main = consublist testdata
