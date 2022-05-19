-- Char
goal0 :: [Bool]
goal0 = [
    show 'a'     == ['\'', 'a', '\'']
  , show '!'     == ['\'', '!', '\'']
  , show '\0'    == ['\'', '\\', '0', '0', '\'']
  , show '\a'    == ['\'', '\\', 'a', '\'']
  , show '\b'    == ['\'', '\\', 'b', '\'']
  , show '\f'    == ['\'', '\\', 'f', '\'']
  , show '\n'    == ['\'', '\\', 'n', '\'']
  , show '\r'    == ['\'', '\\', 'r', '\'']
  , show '\t'    == ['\'', '\\', 't', '\'']
  , show '\v'    == ['\'', '\\', 'v', '\'']
  , show '\\'    == ['\'', '\\', '\\', '\'']
  , show '\''    == ['\'', '\\', '\'', '\'']
  , show '"'     == ['\'', '"', '\'']
  , show '\65'   == ['\'', 'A', '\'']
  , show '\x41'  == ['\'', 'A', '\'']
  , show '\o101' == ['\'', 'A', '\'']
  ]

{-# ORACLE_RESULT goal1: True #-}
goal1 :: Bool
goal1 = and goal0


-- Int
goal10 :: [Bool]
goal10 = [
    show 1    == ['1']
  , show 0    == ['0']
  , show (-1) == ['-', '1']
  ]

{-# ORACLE_RESULT goal11: True #-}
goal11 :: Bool
goal11 = and goal10


-- Float
goal20 :: [String]
goal20 = [
    show 1.0
  , show 0.0
  , show (-1.0)
  ]


-- String
goal30 :: [Bool]
goal30 = [
    show "Hello" == ['"', 'H', 'e', 'l', 'l', 'o', '"']
  , show "a\nb"  == ['"', 'a', '\\', 'n', 'b', '"']
  , show "'\"'"  == ['"', '\'', '\\', '"', '\'', '"']
  ]

{-# ORACLE_RESULT goal31: True #-}
goal31 :: Bool
goal31 = and goal30


