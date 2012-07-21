module CatLOIS where

import FileGoodies
import IO
import qualified FlatCurry
import qualified FlatCurryToLOIS
import qualified ShowLOIS
import System

main = do
  args <- getArgs
  let input = args !! 0 -- flat curry file

  curryProg <- FlatCurry.readFlatCurryFile input

  let prog = FlatCurryToLOIS.process curryProg
  putStrLn (ShowLOIS.showProgram prog)
