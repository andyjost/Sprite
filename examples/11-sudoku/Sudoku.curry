-- Sudoku by search.
--
-- A board is nine rows of nine Ints.  A zero marks a blank cell.
--
-- `solve` picks the blank cell with the fewest candidates and calls `fill`,
-- which chooses one of the candidates and recurses.  Every completion of the
-- board is one value of `solve`.  A branch dies as soon as a cell has no
-- candidate, because no rule of `fill` matches an empty candidate list.

module Sudoku where

import Data.List ((\\), minimum)

type Board = [[Int]]

-- Every solution of the board.
solve :: Board -> Board
solve b = case blanks b of
  []    -> b
  cells -> let (_, r, c, cands) = minimum cells
           in fill b r c cands

-- Writes one of the candidate digits into cell (r, c) and continues.  The
-- choice between the first candidate and the rest is the search.  Keep the
-- choice here, at the top of the function that makes it.  A choice stored
-- inside the board (`place b r c (anyOf cands)`) is shared by every later
-- look at that cell, and the search then runs out of memory.
fill :: Board -> Int -> Int -> [Int] -> Board
fill b r c (d:ds) = solve (place b r c d) ? fill b r c ds

-- The blank cells.  The candidate count comes first, so `minimum` picks the
-- most constrained cell.
blanks :: Board -> [(Int, Int, Int, [Int])]
blanks b = [ (length cs, r, c, cs)
           | (r, row) <- zip [0..] b
           , (c, v) <- zip [0..] row
           , v == 0
           , let cs = candidates b r c ]

-- The digits that may go into cell (r, c): those not yet in its row, its
-- column, or its 3x3 box.
candidates :: Board -> Int -> Int -> [Int]
candidates b r c = [1..9] \\ (row ++ col ++ box)
  where
    row = b !! r
    col = map (!! c) b
    br  = 3 * (r `div` 3)
    bc  = 3 * (c `div` 3)
    box = [ b !! i !! j | i <- [br .. br + 2], j <- [bc .. bc + 2] ]

-- The board with v written at (r, c).
place :: Board -> Int -> Int -> Int -> Board
place b r c v = [ [ if (i, j) == (r, c) then v else x | (j, x) <- zip [0..] row ]
                | (i, row) <- zip [0..] b ]
