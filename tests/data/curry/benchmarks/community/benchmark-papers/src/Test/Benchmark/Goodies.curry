-----------------------------------------------------------------
--- Some goodies for creating benchmarks.
--- In particular, this module defines some operations to
--- visualize benchmark results.
---
--- @author Michael Hanus
--- @version May 2021
-----------------------------------------------------------------

module Test.Benchmark.Goodies
  ( showF2,
    benchInputsResultsAsTable, benchResultsAsTable, toTableRow,
    PlotStyle(..), plotResults
  )
 where

import Data.List       ( intercalate )
import System.FilePath ( dropExtension, takeExtension )
import System.Process  ( system )

-----------------------------------------------------------------------
-- Operations to format data as strings.

-- Shows a floating point number with two decimals.
showF2 :: Float -> String
showF2 x = let (xs,ys) = break (=='.') (show x)
            in if null ys then xs ++ ".00"
                          else xs ++ "." ++ take 2 (tail ys ++ repeat '0')

-----------------------------------------------------------------------
-- Operations for showing benchmark results as latex tables.

--- Format simple benchmark results (i.e., a list of input/result pairs)
--- as a latex table consisting of a row for input values and a row
--- for result values. The first argument is a pair of labels for the
--- input/results rows.
benchInputsResultsAsTable :: (String,String) -> [(String,String)] -> String
benchInputsResultsAsTable (ilabel,rlabel) xs =
  "\\begin{tabular}{|l|" ++ concat (take (length xs) (repeat "c|")) ++ "}\n" ++
  "\\hline\n" ++
  toTableRow (ilabel : map (\ (n,_) -> n) xs) ++
  toTableRow (rlabel : map (\ (_,t) -> t) xs) ++
  "\\hline\n\\end{tabular}\n"

--- Format benchmark results as a LaTeX table.
--- The results are given as a table, i.e., as a list of rows.
--- The first argument is the list of column labels for the
--- benchmark data (second argument).
benchResultsAsTable :: [String] -> [[String]] -> String
benchResultsAsTable colnames xs =
  "\\begin{tabular}{|" ++ concat (take (length colnames) (repeat "r|")) ++ "}\n" ++
  "\\hline\n" ++
  toTableRow colnames ++
  "\\hline\n" ++
  concatMap toTableRow xs ++
  "\\hline\n\\end{tabular}\n"

--- Shows a list of strings as a LaTeX table row.
toTableRow :: [String] -> String
toTableRow xs = intercalate " & " xs ++" \\\\\n"

-----------------------------------------------------------------------
-- Operations for plotting benchmark results.

--- The various parameters to influence the style of the plot.
--- @cons Lines - a line style plot
--- @cons Histogram - a histogram style plot
--- @cons Title - the main title of the plot
--- @cons XLabel - the label of the x axis
--- @cons YLabel - the label of the y axis
--- @cons XTicsRotate - the rotation of the tics on the x axis
data PlotStyle = Lines
               | Histogram
               | Title String
               | XLabel String
               | YLabel String
               | XTicsRotate Int
 deriving Eq

--- Transform plot styles into gnuplot commands.
plotStyle2GP :: PlotStyle -> String
plotStyle2GP Lines = "set style data linespoints\n" ++
                     "set key right bottom"
plotStyle2GP Histogram = "set style histogram clustered\n" ++
                         "set style data histograms"
plotStyle2GP (Title s) = "set title \"" ++ s ++ "\""
plotStyle2GP (XLabel s) = "set xlabel \"" ++ s ++ "\""
plotStyle2GP (YLabel s) = "set ylabel \"" ++ s ++ "\""
plotStyle2GP (XTicsRotate a) = "set xtics rotate by " ++ showInt a

showInt :: Int -> String
showInt i = if i<0 then '-' : show (-i) else show i

--- Visualize a list of benchmarks results (i.e., lists of input/run-time pairs)
--- as a plot graphic with gnuplot. Each benchmark result graph is provided
--- with a title shown in the plot. The first argument is the plot name
--- (i.e., the graphic will be stored in a JPEG file with suffix ".jpg"
--- to this name). Further arguments are the plot style and
--- the data to be plotted (represented as a pair of a title
--- and the (x,y) values to be plotted).
plotResults :: (Show a, Show b) =>
               String -> [PlotStyle] -> [(String,[(a,b)])] -> IO ()
plotResults outfile pstyles titleddata = do
  let pname          = dropExtension outfile
      outsuffix      = takeExtension outfile
      plotfileprefix = pname ++ "_"
      scriptfile     = pname ++ ".gpscript"
      terminalset    = case outsuffix of
        ".pdf" -> "set terminal pdf enhanced"
        ".jpg" -> "set terminal jpeg nocrop enhanced"
        _ -> error $ "plotResults: unsupported out file format: " ++ outsuffix
  titleddatafiles <- mapM (writeDataFile plotfileprefix) (zip [1..] titleddata)
  writeFile scriptfile $ unlines $
    [terminalset
    ,"set output '" ++ outfile ++ "'"
    ,"set tics nomirror"
    ,"set style fill solid border"] ++
    map plotStyle2GP pstyles ++
    ["plot " ++ intercalate " , " (map plotCmd titleddatafiles)]
  system $ "gnuplot " ++ scriptfile
  --system $ unwords (["rm",scriptfile] ++ map snd titleddatafiles)
  putStrLn $ "Data plotted to '" ++ outfile ++ "'"
 where
  plotCmd (title,datfile) =
    "\"" ++ datfile ++ "\" " ++
    (if Histogram `elem` pstyles then "using 2:xtic(1) " else "") ++
    (if null title then "notitle" else "title \"" ++ title ++ "\"")

    -- Further parameters:
    -- pt 5 : select specific point type
    -- lc rgb "black" : select black color

-- Write data into file for gnuplot:
writeDataFile :: (Show a, Show c, Show d) =>
                 String -> (a,(b,[(c,d)])) -> IO (b,String)
writeDataFile fileprefix (n,(title,bdata)) = do
  let datafilename = fileprefix ++ show n ++ ".dat"
  writeFile datafilename
            (unlines (map (\ (x,y) -> show x ++ "\t" ++ show y) bdata))
  return (title,datafilename)

-----------------------------------------------------------------------
-- Tests:
test1 :: IO ()
test1 =
 plotResults "xxx.jpg"
   [Lines, Title "nrev run times",
    XLabel "list length", YLabel "run time (seconds)"]
   [data1,data2]

test2 :: IO ()
test2 =
 plotResults "xxx.pdf"
   [Histogram, Title "nrev run times",
    XLabel " ",
    XTicsRotate (-45),
    YLabel "run time (seconds)"]
   [data1,data2]

data1 :: (String, [(Int, Float)])
data1 = ("pakcs",
         [(500,0.09666666666666668)
         ,(1000,0.3433333333333333)
         ,(1500,0.8533333333333334)
         ,(2000,1.6899999999999997)
         ,(2500,3.0066666666666664)
         ])

data2 :: (String, [(Int, Float)])
data2 = ("kics2",
         [(500,0.0)
         ,(1000,0.01)
         ,(1500,0.02)
         ,(2000,0.03)
         ,(2500,0.056666666666666664)
         ,(3000,0.08333333333333333)
         ,(3500,0.12)
         ,(4000,0.17)
         ,(4500,0.22)
         ,(5000,0.28)
         ,(5500,0.36000000000000004)
         ,(6000,0.44)
         ,(6500,0.53)
         ])

-----------------------------------------------------------------------
