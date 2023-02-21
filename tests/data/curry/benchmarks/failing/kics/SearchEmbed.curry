embed :: String -> String -> Int -> Success
embed []     _ _ = success
embed (c:cs) t n = t =:= x++(c:ts) & length x + 1 =:= n & embed cs ts n
  where x, ts free

embedded :: String -> String -> Int
embedded s t | embed s t n = n where n free

makeGoal n = embedded (concat (take n (repeat "Hello World")))
                      (concat (take n (repeat  "aHaealalaoa aWaoaralad")))

main = makeGoal 10