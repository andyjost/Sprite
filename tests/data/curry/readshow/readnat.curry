goal1 :: Int
goal1 = read "1"

goal2 :: Int
goal2 = read ""

goal3 :: Int
goal3 = read "a"

goal4 :: Int
goal4 = read "1x"

goal5 :: Int
goal5 = read "1."

goal6 :: Int
goal6 = read "1 "

goal7 :: Int
goal7 = read " 1"

goal8 :: Int
goal8 = read "-1"

goal9 :: Int
goal9 = read "(-1)"

goal10 :: Int
goal10 = read "(1)"

goal11 :: Int
goal11 = read "0"

goal12 :: Int
goal12 = read "-0"

goal13 :: Int
goal13 = read "+0"

goal14 :: Int
goal14 = read "+1"

goal15 :: Int
goal15 = read " "

goal16 :: [Int]
goal16 = [
    read "123",
    read "-1",
    read "9223372036854775807",
    read "-9223372036854775807"
  ]

-- Fails b/c the Prelude tries the construct the (non-representable) positive
-- and then negate it.
-- goal_fail :: Int
-- goal_fail = read "-9223372036854775808"
