import System
import Time
import IO
import ReadShowTerm
import ICurry
import Block
import ICurryToCpp
import Makefile

trace = False  -- toggle for tracing

trace :: Bool
main :: IO ()
main = do
  args <- getArgs
  foldr ((>>) . process_file) (return ()) args

process_file :: String -> IO ()
process_file file = do 
  icur_handle <- openFile (file ++ ".icur") ReadMode
  icur_contents <- hGetContents icur_handle
  if trace
    then do
      putStrLn "--------- CONTENT INITIAL ---------"
      putStrLn (show icur_contents)
    else done


  let icurry = readQTerm icur_contents
  if trace
    then do
      putStrLn "--------- ICURRY INITIAL ---------"
      putStrLn (show icurry)
    else done

  time <- getLocalTime
  let timeStamp = toTimeString time ++ " " ++ toDayString time

  let hpp = ICurryToCpp.icurryToHpp icurry timeStamp
  if trace
    then do
      putStrLn "--------- HPP ---------"
      putStrLn (show hpp)
    else done
  hpp_handle <- openFile (file ++ ".hpp") WriteMode
  hPutStrLn hpp_handle (blockToString hpp)

  let cpp = ICurryToCpp.icurryToCpp icurry timeStamp
  if trace
    then do
      putStrLn "--------- CPP ---------"
      putStrLn (show cpp)
    else done
  cpp_handle <- openFile (file ++ ".cpp") WriteMode
  hPutStrLn cpp_handle (blockToString cpp)

  Makefile.makefile file icurry

