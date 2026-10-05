-- Goals without type signatures, for tests/unit_goals.py.  The front end
-- generalizes each one with class dictionaries as parameters, and the typed
-- boundary defaults the constraints with the table of the PAKCS REPL.
module UnsignedGoals where

main14 = Just 5
main15 = 1 + 2
main16 = return 5
main17 = toEnum 65
main18 = maxBound
main19 = 3 / 2
main20 = fromIntegral 3
main21 = [1, 2.5]
main22 = (1, 'a')
main23 = 2 ^ 3
main24 = []
main25 = id
main26 = pure (1, 'a')
main27 = mapM_ print [1, 2]
main28 = fmap (+1) (Just 1)
main29 = let x, y free in (x =:= y, x)
main30 = show (1 + 2)
main31 = take 3 [1 ..]
main32 = maxBound + 1

addOne x = x + 1

main33 :: Int
main33 = 7
