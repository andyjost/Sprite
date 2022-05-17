goal1 :: Float
goal1 = read "1"

goal2 :: Float
goal2 = read ""

goal3 :: Float
goal3 = read "a"

goal4 :: Float
goal4 = read "1x"

goal5 :: Float
goal5 = read "1."

goal6 :: Float
goal6 = read "1 "

goal7 :: Float
goal7 = read " 1"

goal8 :: Float
goal8 = read "-1"

goal9 :: Float
goal9 = read "(-1)"

goal10 :: Float
goal10 = read "(1)"

goal11 :: Float
goal11 = read "0"

goal12 :: Float
goal12 = read " "

goal13 :: Float
goal13 = read "."

goal14 :: Float
goal14 = read ".1"

goal15 :: Float
goal15 = read ".1."

goal16 :: [Float]
goal16 = [
    read "123",
    read "-1",
    read "9223372036854775807",
    read "-9223372036854775808",
    read "0.123",
    read "+0.123",
    read "-0.123",
    read ".123",
    read "+.123",
    read "-.123",
    read "0.",
    read "0.0",
    read "12.",
    read "+12.",
    read "-12.",
    read "12.34",
    read "+12.34",
    read "-12.34"
  ]
