module Geo where

data Point = Point Int Int deriving (Eq, Show)

data Tree = Leaf | Node Tree Int Tree deriving (Eq, Show)

origin :: Point
origin = Point 0 0

norm1 :: Point -> Int
norm1 (Point x y) = abs x + abs y
