-- Fibonacci numbers:
fibs = fibgen 1 1
fibgen n1 n2 = n1 : fibgen n2 (n1+n2)

isFib (_:x) = isFib x
isFib []    = True

main :: Bool
main = isFib (take 500000 fibs)
