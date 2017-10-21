-- Convert FlatCurry to ICurry
-- Sergio Antoy
-- Mon Apr 28 10:51:09 PDT 2014

import System
import IO
import FlatCurry.Types
import FlatCurry.Files
import FlatCurry.Read


import ICurry
import TypeTable
-- import VarTable
-- import CountRef
import PPFlat
import FlatToICurry
import PPICurry_Ex
-- import PPICurry
import FixCount
import RemoveInnerCases
import RemoveInnerLets

trace = False  -- toggle for tracing

main :: Prelude.IO ()
main = do
  args <- getArgs
  foldr ((>>) . process_file) (return ()) args

process_file :: [Prelude.Char] -> Prelude.IO ()
process_file file = do 
  flat <- readFlatCurry file
  if trace
    then do
      putStrLn "--------- FLAT INITIAL ---------"
      putStrLn (PPFlat.execute flat)
    else done

  -- Find constructors used by the program, but defined in other modules.
  modules <- readFlatCurryIntWithImports file
  let type_table = TypeTable.execute modules
  if trace
    then do
      putStrLn "--------- TYPE TABLE ---------"
      putStrLn (ppTypeTable type_table)
    else done

  -- Replace case statements that are arguments of an application
  -- with new functions.
  let non_inner_cases = RemoveInnerCases.execute flat
  if trace
    then do
      putStrLn "--------- NO INNER CASES ---------"
      putStrLn (show non_inner_cases)
      putStrLn (PPFlat.execute non_inner_cases)
    else done

  -- Replace let-blocks that are arguments of an application
  -- with new functions.
  let non_inner_lets = RemoveInnerLets.execute non_inner_cases
  if trace
    then do
      putStrLn "--------- NO INNER LETS ---------"
      putStrLn (PPFlat.execute non_inner_lets)
    else done

  let icurry = FlatToICurry.execute type_table non_inner_lets
  let n = FixCount.execute icurry
  -- force the execution of FixCount
  icurry_handle <- seq n (openFile (file ++ ".icur") WriteMode)
  hPutStr icurry_handle (show icurry)
  hClose icurry_handle

  if trace
    then do
      putStrLn "--------- ICURRY ---------"
      putStrLn (show icurry)
      putStrLn (PPICurry_Ex.execute icurry)
    else done

  read_handle <- openFile (file ++ ".read") WriteMode
  hPutStrLn read_handle (PPICurry_Ex.execute icurry)
  hClose read_handle
