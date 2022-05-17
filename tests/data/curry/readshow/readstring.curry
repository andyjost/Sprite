goal1 :: String
goal1 = read ""

goal2 :: String
goal2 = read "a"

goal3 :: String
goal3 = read "'a'"

goal4 :: String
goal4 = read "1"

goal5 :: String
goal5 = read "1."

goal6 :: String
goal6 = read "\"Hello"

goal7 :: String
goal7 = read "\"Hello\""

goal8 :: Bool
goal8 = read "\"Hello\nWorld!\"" == "Hello\nWorld!"

goal9 :: Bool
goal9 = read "\"\\a\a'\"" == "\a\a'"

goal10 :: String
goal10 = read "\"\\ \""

