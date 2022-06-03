goal1 :: Char
goal1 = read "'a'"

goal2 :: Char
goal2 = read "a"

goal3 :: Char
goal3 = read ""

goal4 :: Char
goal4 = read "'a'junk"

goal5 :: (Char, Char, Char, Char, Char, Char, Char)
goal5 = (read "'\\a'",
         read "'\\b'",
         read "'\\f'",
         read "'\\n'",
         read "'\\r'",
         read "'\\t'",
         read "'\\v'")

goal6 :: (Char, Char, Char, Char, Char, Char, Char)
goal6 = (read "'\a'",
         read "'\b'",
         read "'\f'",
         read "'\n'",
         read "'\r'",
         read "'\t'",
         read "'\v'")

goal7 :: (Char, Char, Char, Char)
goal7 = (read "'\\\\'",
         read "'\\\"'",
         read "'\\\''",
         read "'\\''")

goal8 :: [(String, String)]
goal8 = readList "['a', 'b', 'c']"

goal9 :: Char
goal9 = read "'\\65'"

goal10 :: Char
goal10 = read "'\65'"

{-# ORACLE_RESULT goal11: 'A' #-}
goal11 :: Char
goal11 = read "'\\x41'"

goal12 :: Char
goal12 = read "'\x41'"

{-# ORACLE_RESULT goal13: 'A' #-}
goal13 :: Char
goal13 = read "'\\x041'"

goal14 :: Char
goal14 = read "'\x041'"

{-# ORACLE_RESULT goal15: 'A' #-}
goal15 :: Char
goal15 = read "'\\o101'"

goal16 :: Char
goal16 = read "'\o101'"
