data T = C1 | C2 | C3 | C4

f x = case x of
  C1 -> True
  y  -> case y of
    C2 -> False
    z  -> case z of
      C1 -> True
      _  ->  not False

g x = case x of
  1 -> 1
  2 -> 2
  x -> x
