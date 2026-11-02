module PrimitiveIO where
import System.IO
import System.Directory
import System.Process
import Data.Time (clockTimeToInt)
import Debug.Trace

writeText :: String -> String -> IO ()
writeText path text = withFile path WriteMode (\h -> hPutStr h text)
appendText :: String -> String -> IO ()
appendText path text = withFile path AppendMode (\h -> hPutStr h text)
readText :: String -> IO String
readText path = openFile path ReadMode >>= hGetContents
seekText :: String -> IO Char
seekText path = withFile path ReadMode (\h -> do
  hSeek h SeekFromEnd (-1)
  hSeek h RelativeSeek 0
  hGetChar h)
absoluteText :: String -> IO Char
absoluteText path = withFile path ReadMode (\h -> hSeek h AbsoluteSeek 0 >> hGetChar h)
closed :: String -> IO Char
closed path = do h <- openFile path ReadMode
                 hClose h
                 hGetChar h
identity :: String -> IO Bool
identity path = do a <- openFile path ReadMode
                   b <- openFile path ReadMode
                   hClose a
                   hClose a
                   hClose b
                   return (a == a && a /= b && stdout == stdout && stdout /= stderr)
properties :: String -> IO (Bool,Bool)
properties path = withFile path ReadMode (\h -> do
  readable <- hIsReadable h
  writable <- hIsWritable h
  return (readable,writable))
eof :: String -> IO Bool
eof path = withFile path ReadMode (\h -> do
  hGetChar h
  hIsEOF h)
ready :: String -> IO (Bool,Int)
ready path = withFile path ReadMode (\h -> do
  b <- hWaitForInput h 0
  i <- hWaitForInputs [h] 0
  return (b,i))
output :: IO ()
output = putStr "P" >> hPutStr stdout "H" >> hFlush stdout
choiceOutput :: IO ()
choiceOutput = hPutStr stdout "A" ? hPutStr stdout "B"
traceValue :: IO ()
traceValue = traceIO "trace message"
pipeTerminal :: IO Bool
pipeTerminal = hIsTerminalDevice stdin
pipeReady :: IO Bool
pipeReady = hWaitForInput stdin 1000
pipeReadyIndex :: IO Int
pipeReadyIndex = hWaitForInputs [stdin] 1000
stdInput :: IO (Char,Char)
stdInput = do a <- getChar
              hIsEOF stdin
              b <- hGetChar stdin
              return (a,b)
modification :: String -> IO Int
modification path = getModificationTime path >>= return . clockTimeToInt
exitTest :: IO ()
exitTest = exitWith 23
