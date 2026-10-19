module Hello where

greet :: String -> String
greet name = "Hello, " ++ name ++ "!"

number :: Int
number = 1 ? 2 ? 3

nothing :: Int
nothing = failed

bad :: Int
bad = 1 `div` 0
