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
import PPFlat
import FlatToICurry
import PPICurry_Ex
-- import PPICurry
import FixCount
-- import RemoveInnerCases
-- import RemoveInnerLets

import C_Like_Expr_fy
import Case_Select_Var_fy

trace :: Bool
trace = False  -- toggle for tracing

main :: Prelude.IO ()
main = do
  args <- getArgs
  foldr ((>>) . process_file) (return ()) args

process_file :: [Prelude.Char] -> Prelude.IO ()
process_file file = do
  sysPath <- getEnviron "CURRYPATH" -- CURRYPATH for this script.
  tgtPath <- getEnviron "TARGET_CURRYPATH" -- CURRYPATH for the target program.
  if tgtPath /= "" then do setEnviron "CURRYPATH" tgtPath else done
  flat <- readFlatCurry file
  if trace
    then do
      putStrLn "--------- FLAT INITIAL ---------"
      putStrLn (PPFlat.execute flat)
    else done

  -- Find constructors used by the program, but defined in other modules.
  modules <- readFlatCurryIntWithImports file
  setEnviron "CURRYPATH" sysPath
  let type_table = TypeTable.execute modules
  if trace
    then do
      putStrLn "--------- TYPE TABLE ---------"
      putStrLn (ppTypeTable type_table)
    else done

  -- putStrLn "--------- FLAT INITIAL ---------"
  -- putStrLn (PPFlat.execute flat)

  -- Transform expressions with nested statements into C-like expressions
  let c_like_expr = C_Like_Expr_fy.execute flat
  if trace
    then do
      putStrLn "--------- After C-like ---------"
      putStrLn (show flat)
      putStrLn (show c_like_expr)
    else done

  --putStrLn "--------- After C-like ---------"
  --putStrLn (PPFlat.execute c_like_expr)

  -- Ensure the selector of a case statement is a variable
  let case_select_var = Case_Select_Var_fy.execute c_like_expr
  if trace
    then do
      putStrLn "--------- After Case select var ---------"
      putStrLn (show case_select_var)
    else done

  -- Convert to ICurry
  let icurry = FlatToICurry.execute type_table case_select_var
  let n = FixCount.execute icurry
  -- force the execution of FixCount
  icurry_handle <- seq n (openFile (file ++ ".icur") WriteMode)
  hPutStr icurry_handle (show icurry)
  hClose icurry_handle

  --putStrLn "--------- After Case select var ---------"
  --putStrLn (PPFlat.execute case_select_var)

  if trace
    then do
      putStrLn "--------- ICURRY ---------"
      putStrLn (show icurry)
      putStrLn (PPICurry_Ex.execute icurry)
    else done

--  putStrLn (PPICurry_Ex.execute icurry)

  read_handle <- openFile (file ++ ".read") WriteMode
  hPutStrLn read_handle (PPICurry_Ex.execute icurry)
  hClose read_handle

