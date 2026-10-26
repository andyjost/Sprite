-- "Blocks World" solver for intermediate problems

{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}

import Control.Search.SetFunctions
import Data.List ( isSuffixOf )

data Block = A | B | C | D | E deriving Eq
type Stack = [Block]
type World = (Stack, Stack, Stack)
type Trace = [World]
data Problem = Problem World World

simpleProblem, difficultProblem :: Problem
simpleProblem = Problem ([A,B],[],[]) ([],[A,B],[])
difficultProblem = Problem ([A,B,C,D,E],[],[]) ([],[C,B,A,D,E],[])

moveToGoal :: World -> World -> World
moveToGoal (x:xs, ys, zs) (_, _++x:ys, _) = (xs, x:ys, zs) -- p -> q
moveToGoal (x:xs, ys, zs) (_, _, _++x:zs) = (xs, ys, x:zs) -- p -> r
moveToGoal (xs, y:ys, zs) (_++y:xs, _, _) = (y:xs, ys, zs) -- q -> p
moveToGoal (xs, y:ys, zs) (_, _, _++y:zs) = (xs, ys, y:zs) -- q -> r
moveToGoal (xs, ys, z:zs) (_++z:xs, _, _) = (z:xs, ys, zs) -- r -> p
moveToGoal (xs, ys, z:zs) (_, _++z:ys, _) = (xs, z:ys, zs) -- r -> p
moveToGoal'default w g = noMoveFromGoal w g

noMoveFromGoal :: World -> World -> World
noMoveFromGoal (x:xs, ys, zs) (g, _, _)
  | not (isSuffixOf (x:xs) g) = (xs, x:ys, zs) ? (xs, ys, x:zs)
noMoveFromGoal (xs, y:ys, zs) (_, g, _)
  | not (isSuffixOf (y:ys) g) = (y:xs, ys, zs) ? (xs, ys, y:zs)
noMoveFromGoal (xs, ys, z:zs) (_, _, g)
  | not (isSuffixOf (z:zs) g) = (z:xs, ys, zs) ? (xs, z:ys, zs)

extend :: Trace -> World -> Trace
extend trace@(t:ts) goal
  | t == goal    = reverse trace
  | t `elem` ts  = failed
  | otherwise    = extend (moveToGoal t goal : trace) goal

main :: Trace
main = selectValue (set2 extend [s] f) 
     where Problem s f = difficultProblem
