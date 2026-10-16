module Tools where

-- A small module for the transcripts of the tools (stage A of the review).

data Color = Red | Green | Blue
 deriving (Eq, Show)

-- A goal with a free variable in its value.
freegoal :: (Int, Int)
freegoal = (x, 1) where x free

-- A goal with a free variable bound by a constraint; the variable is
-- absent from the result type.
bound :: Bool
bound = xs ++ [3] =:= [1, 2, 3] where xs free

-- A goal with no value.
nothing :: Int
nothing = failed

-- A goal that raises.
boom :: Int
boom = error "boom"

-- A goal with two values.
main :: Int
main = 1 ? 2

-- A goal with a suspension.
suspend :: Bool
suspend = x == (1 :: Int) where x free

-- An IO goal.
hello :: IO ()
hello = putStrLn "hello"

colors :: [Color]
colors = [Red, Green]
