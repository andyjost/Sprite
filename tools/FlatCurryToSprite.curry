module FlatCurryToSprite where

-- import Directory
import FileGoodies
import IO
import qualified FlatCurry
import qualified FlatCurryToLOIS
import qualified LOISToSprite
import System

main = do
  args <- getArgs
  let input = args !! 0
  let output = args !! 1

  -- Open the input and output files.
  curryProg <- FlatCurry.readFlatCurryFile input
  fh <- openFile output WriteMode

  let prog = FlatCurryToLOIS.process curryProg
  let modname = stripSuffix $ baseName input
  LOISToSprite.translate fh modname prog
