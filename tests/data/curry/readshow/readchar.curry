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

goal8 :: Bool
goal8 = readList "Hello\n" == [(['H', 'e', 'l', 'l', 'o', '\n'], [])]

goal9 :: (Char, Char, Char, Char, Char, Char, Char, Char)
goal9 = (read "'\\65'"      , read "'\65'",
         read "'\\x41'"     , read "'\x41'",
         read "'\\x041'"    , read "'\x041'",
         read "'\\o101'"    , read "'\o101'")
