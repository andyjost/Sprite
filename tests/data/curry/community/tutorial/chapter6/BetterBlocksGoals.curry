-- Finite instances of the unchanged tutorial solver.
module BetterBlocksGoals where

import qualified betterblocks as B

-- Enumerate every solution of the finite two-block problem.
solveSimple = B.extend [s] f
  where B.Problem s f = B.simpleProblem

fallbackMove = B.moveToGoal ([B.A,B.B],[],[]) ([],[B.A,B.B],[])

moveToFinal = B.moveToGoal ([B.A],[],[]) ([],[B.A],[])

-- The default rule has no legal move away from a completed goal.
noMoveFromFinal = B.moveToGoal ([],[B.A],[]) ([],[B.A],[])
