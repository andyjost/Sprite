module CursorFail where

data Bit = O | I
data Pair = Pair Bit Bit
loop :: Bit
loop = loop
main = let b = failed in Pair O b ? Pair loop b
