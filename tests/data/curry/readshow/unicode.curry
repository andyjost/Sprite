-- A Char is a Unicode code point.  show writes a code point outside
-- printable ASCII as a decimal escape.  The source holds raw UTF-8 as well
-- as escapes.

goal1 :: Bool
goal1 = show '\228' == "'\\228'"

goal2 :: [Int]
goal2 = map ord "äöü"

goal3 :: Bool
goal3 = show "a\228\246\252" == "\"a\\228\\246\\252\""

goal4 :: Int
goal4 = ord (chr 160)

goal5 :: Bool
goal5 = show (chr 128512) == "'\\128512'"

goal6 :: Bool
goal6 = read "'\\228'" == 'ä'

goal7 :: Bool
goal7 = (read "\"\\228\\246\\252\"" :: String) == "äöü"

goal8 :: [Int]
goal8 = map ord (show (chr 127) ++ show (chr 126) ++ show (chr 0))

goal9 :: Int
goal9 = length "äöü😀"

goal10 :: [Int]
goal10 = map (ord . chr) [0, 127, 128, 160, 255, 256, 65535, 65536, 1114111]
