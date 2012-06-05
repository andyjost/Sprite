module FlatCurryToSpriteMain where

import FileGoodies
import IO
import qualified FlatCurry
import qualified FlatCurryToLOIS
import qualified LOISToSprite
import System

main = do
  args <- getArgs
  let modname = args !! 0 -- module name
  let output = args !! 1 -- output file

  -- Open the input and output files.
  -- curryProg <- FlatCurry.readFlatCurryFile input
  fh <- openFile output WriteMode

  -- let prog = FlatCurryToLOIS.process curryProg
  -- let modname = stripSuffix $ baseName input
  LOISToSprite.translateMain fh modname
