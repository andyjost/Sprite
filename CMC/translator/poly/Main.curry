-- Extends ICurry with some functions such as equality

import System
import IO
import ReadShowTerm
import ICurry
import PPICurry
-- import PPICurry_Ex
import BoolEqual
import ConstrainEqual
import Compare
import Show

main = do
  args <- getArgs
  foldr ((>>) . process_file) (return ()) args

process_file file = do 
  icur_handle <- openFile (file ++ ".icur") ReadMode
  icur_contents <- hGetContents icur_handle
  -- putStrLn (show icur_contents)

  let code = readQTerm icur_contents
  -- putStrLn "  ----- ICurry -----"
  -- putStrLn (PPICurry_Ex.execute code)

  let boolEqual = BoolEqual.execute code
  let constrainEqual = ConstrainEqual.execute code
  let compare = Compare.execute code
  let xshow = Show.execute code
  -- putStrLn ((foldr ((++) . PPICurry_Ex.ppFunction) "\n") poly)
  let (IModule name imported_list data_list funct_list) = code
  let extended = IModule name imported_list data_list 
                   (funct_list ++ boolEqual ++ constrainEqual ++ compare ++ xshow)
  poly_handle <- openFile (file ++ ".poly") WriteMode
  hPutStr poly_handle (show extended)
  -- putStrLn "  ----- ICurry -----"
  -- putStrLn (PPICurry_Ex.execute extended)

  read_handle <- openFile (file ++ ".read") WriteMode
  hPutStrLn read_handle (PPICurry.execute extended)
  -- hPutStrLn read_handle (PPICurry_Ex.execute extended)
  hClose read_handle
