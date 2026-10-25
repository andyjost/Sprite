------------------------------------------------------------------------------
--- A DSL for benchmark descriptions embedded into Curry
---
--- @author Michael Hanus
--- @version May 2021
------------------------------------------------------------------------------

module Test.Benchmark
  ( Benchmark, benchmark, prepareBenchmarkCleanup,
    withPrepare, withCleanup,
    iterateBench, (**>),
    mapBench, pairBench, diffBench, (.-.),
    runOn, runUntilOn, runUntilNothingOn, execBench,
    benchTimeNF, benchCommandOutput,
    CmdResult, cmdResultAverage,
    exitStatus, elapsedTime, cpuTime, systemTime,
    maxResidentMemory,
    benchCommand, benchCommandWithLimit,
    elapsedTime4Command, cpuTime4Command,
    getHostName, getOS, getSystemID, getSystemRelease, 
    getSystemDescription, getCoreNumber, getCPUModel
  )
 where

import Data.List      ( isPrefixOf )
import System.IO      ( hGetContents )

import System.IOExts  ( connectToCommand, evalCmd, readCompleteFile )
import System.Process ( getPID, system )

import Debug.Profile

------------------------------------------------------------------------------
--- Representation of benchmarks.
--- A benchmark consists of some preparation, e.g., to generate
--- benchmark data, some final cleanup, and the benchmark itself.
--- If a benchmark is executed several times, the preparation and
--- cleanup work is done only once.
data Benchmark a = BM (IO ()) (IO ()) (IO a)

--- A benchmark is basically an I/O action to compute the benchmark results.
benchmark :: IO a -> Benchmark a
benchmark bench = BM (return ()) (return ()) bench

--- Benchmarks are functors.
instance Functor Benchmark where
  fmap f (BM pre post action) = BM pre post $ action >>= return . f

--- Benchmarks have an `Applicative` structure.
instance Applicative Benchmark where
  pure x = benchmark (return x)

  fbench <*> abench = benchmark $
    execBench fbench >>= \f -> execBench abench >>= \x -> return (f x)


--- Benchmarks have a monadic structure.
instance Monad Benchmark where
  bench1 >>= abench2 =
    benchmark $ execBench bench1 >>= \x -> execBench (abench2 x)


--- Maps benchmark results according to a given mapping (first argument).
mapBench :: (a -> b) -> Benchmark a -> Benchmark b
mapBench f (BM pre post action) = BM pre post $ action >>= return . f

--- Combines two benchmarks to a single benchmark where the results
--- are paired.
pairBench :: Benchmark a -> Benchmark b -> Benchmark (a,b)
pairBench bench1 bench2 = benchmark $
  execBench bench1 >>= \x -> execBench bench2 >>= \y -> return (x,y)


--- Adds some initial preparation action to a benchmark, e.g., to generate
--- benchmark data.
--- If the benchmark already contains some preparation, this new
--- preparation is executed first.
withPrepare :: Benchmark a -> IO () -> Benchmark a
withPrepare (BM pre post bench) newpre = BM (newpre >> pre) post bench

--- Adds some final cleanup action to a benchmark.
--- If the benchmark already contains some cleanup action, this new
--- cleanup is executed last.
withCleanup :: Benchmark a -> IO () -> Benchmark a
withCleanup (BM pre post bench) newpost = BM pre (post >> newpost) bench

--- A benchmark with some preparation and some final cleanup.
--- In this case, the preparation and cleanup work tightly belongs
--- to the benchmark, i.e., it is repeated with every iteration of
--- the benchmark.
prepareBenchmarkCleanup :: IO () -> IO a -> IO () -> Benchmark a
prepareBenchmarkCleanup pre bench post =
  benchmark $ execBench (BM pre post bench)

------------------------------------------------------------------------------
-- Repeatable benchmarks

--- The class of benchmark results which supports multiple runs by
--- computing the average of a non-empty(!) list of multiple results.
class MultiRunnable a where
  average :: [a] -> a

instance MultiRunnable Int where
  average xs = foldr (+) 0 xs `div` (length xs)

instance MultiRunnable Float where
  average xs = foldr (+) 0.0 xs / fromInt (length xs)

instance MultiRunnable a => MultiRunnable (Maybe a) where
  average = maybe Nothing (Just . average) . sequence

--- Iterates a benchmark multiple times and computes the average result.
--- The preparation and cleanup actions of the benchmark are
--- only executed once, i.e., they are not iterated.
--- The number of executions (first argument) must be postive.
(**>) :: MultiRunnable a => Int -> Benchmark a -> Benchmark a
num **> (BM pre post action) = BM pre post $
  mapM (\_ -> action) [1 .. num] >>= \rs -> return (average rs)

--- Iterates a benchmark multiple times and computes the average according
--- to a given average function (first argument).
--- The preparation and cleanup actions of the benchmark are
--- only executed once, i.e., they are not iterated.
iterateBench :: ([a] -> b) -> Int -> Benchmark a -> Benchmark b
iterateBench averagef n (BM pre post action) = BM pre post $
  mapM (\_ -> action) [1..n] >>= \rs -> return (averagef rs)

------------------------------------------------------------------------------

--- Computes the difference between two benchmarks according to a given
--- difference operation (first argument).
--- This could be useful to evaluate some kernel of a computation where
--- the ressources to prepare the benchmark data are measured by
--- a separate benchmark and subtracted with this operation.
diffBench :: (a -> a -> a) -> Benchmark a -> Benchmark a -> Benchmark a
diffBench minus bench1 bench2 =
  mapBench (uncurry minus) (pairBench bench1 bench2)

--- Computes the numeric difference between two Float-valued benchmarks.
--- This could be useful to evaluate some kernel of a computation where
--- the resources to prepare the benchmark data are measured by
--- a separate benchmark and subtracted with this operation.
(.-.) :: Benchmark Float -> Benchmark Float -> Benchmark Float
bench1 .-. bench2 = diffBench (-) bench1 bench2

--- Runs a parameterized benchmark on a list of input data.
--- The result is a benchmark returning a list of pairs consisting
--- of the input data and the benchmark result for this input data.
---
--- @param bench - the benchmark parameterized by the input data
--- @param benchdata - the list of input data for the benchmarks
--- @return Benchmark with the list of input data and benchmark results pairs
runOn :: (a -> Benchmark b) -> [a] -> Benchmark [(a,b)]
runOn bench xs =
  benchmark $ mapM (\x -> execBench (bench x) >>= \y -> return (x,y)) xs

--- Runs a `Maybe` benchmark on an (infinite) input list of values
--- until a benchmark delivers `Nothing`.
---
--- @param bench - the `Maybe` benchmark parameterized by the input data
--- @param benchdata - the list of input data for the benchmarks
--- @return Benchmark with the list of input data and benchmark results pairs
runUntilOn :: (a -> Benchmark b) -> (b -> Bool) -> [a] -> Benchmark [(a,b)]
runUntilOn _ _ [] = return []
runUntilOn bench stop (x:xs) = do
  bmresult <- bench x
  if stop bmresult
    then return []
    else do results <- runUntilOn bench stop xs
            return ((x,bmresult):results)

--- Run a `Maybe` benchmark on an (infinite) input list of values
--- until a benchmark delivers `Nothing`.
---
--- @param bench - the `Maybe` benchmark parameterized by the input data
--- @param benchdata - the list of input data for the benchmarks
--- @return Benchmark with the list of input data and benchmark results pairs
runUntilNothingOn :: Eq b => (a -> Benchmark (Maybe b)) -> [a]
                          -> Benchmark [(a,b)]
runUntilNothingOn bench benchdata =
  mapBench (map (\ (x,Just y) -> (x,y)))
           (runUntilOn bench (==Nothing) benchdata)

--- Executes a benchmark and returns the benchmark results.
execBench :: Benchmark a -> IO a
execBench (BM pre post action) = do
  pre
  result <- action
  post
  return result

-----------------------------------------------------------------
-- Now we define some constructors to create concrete benchmarks.
-----------------------------------------------------------------
-- A quite simple constructor for internal tests of the Curry system.

--- Benchmark the time (in seconds)
--- to compute the normal form of an expression.
--- The expression is created by an I/O action (first parameter).
--- This avoids the sharing of the normalization process between multiple
--- runs of the benchmark and provides more flexibility, e.g.,
--- to read benchmark input data from global variables.
benchTimeNF :: IO a -> Benchmark Float
benchTimeNF getexp = benchmark $ do
  garbageCollect
  garbageCollectorOff
  pi1 <- getProcessInfos
  exp <- getexp
  seq (id $!! exp) (return ())
  pi2 <- getProcessInfos
  garbageCollectorOn
  let rtime = maybe 0 id (lookup RunTime pi2)
              - maybe 0 id (lookup RunTime pi1)
  return (fromInt rtime / 1000.0)

-----------------------------------------------------------------
-- Benchmarks returning the output of system commands.

--- This operation constructs a benchmark that simply returns
--- the output of a shell command. To be more precise,
--- the constructed benchmark contains as a result the exit status and
--- the standard and error output string produced by the execution
--- of the given shell command (provided as the argument).
benchCommandOutput :: String -> Benchmark (Int,String,String)
benchCommandOutput cmd = benchmark $ evalCmd cmd [] ""

-----------------------------------------------------------------
-- Benchmarks for timing system commands.

--- The result type for benchmarks timing the executing a shell command.
--- Currently, a result contains the command, exit status, elapsed time,
--- cpu time, system time (in seconds), and the maximum resident size
--- (in Kilobytes).
data CmdResult = CD String Int Float Float Float Int

--- The average of a non-empty list of command benchmark results.
--- The exit status average is zero of all are zero.
instance MultiRunnable CmdResult where
  average cds =
    CD (if null cds then "" else (cmdString (head cds)))
       (if all (==0) (map exitStatus cds) then 0 else 1)
       (average (map elapsedTime cds))
       (average (map cpuTime     cds))
       (average (map systemTime  cds))
       (average (map maxResidentMemory cds))

--- The average of a list of command benchmark results.
--- The exit status average is zero of all are zero.
cmdResultAverage :: [CmdResult] -> CmdResult
cmdResultAverage = average

--- The command string of the command benchmark result.
cmdString :: CmdResult -> String
cmdString (CD cs _ _ _ _ _) = cs

--- The exit status of the command benchmark result.
exitStatus :: CmdResult -> Int
exitStatus (CD _ s _ _ _ _) = s

checkExitStatus :: String -> Int -> a -> a
checkExitStatus cmd s x =
  if s == 0
    then x
    else error $ "Benchmark command '" ++ cmd ++ "' has exit status " ++ show s

--- The elapsed time (in seconds) of the command benchmark result.
--- If the exit status is non-zero, an error is raised.
elapsedTime :: CmdResult -> Float
elapsedTime (CD cs s e _ _ _) = checkExitStatus cs s e

--- The cpu time (in seconds) of the command benchmark result.
--- If the exit status is non-zero, an error is raised.
cpuTime :: CmdResult -> Float
cpuTime (CD cs s _ c _ _) = checkExitStatus cs s c

--- The system time (in seconds) of the command benchmark result.
--- If the exit status is non-zero, an error is raised.
systemTime :: CmdResult -> Float
systemTime (CD cs s _ _ st _) = checkExitStatus cs s st

--- The maximum resident size (in Kilobytes) of the command benchmark result.
--- If the exit status is non-zero, an error is raised.
maxResidentMemory :: CmdResult -> Int
maxResidentMemory (CD cs s _ _ _ m) = checkExitStatus cs s m

--- Benchmark the execution of a shell command.
--- Returns benchmark results containing the exit status, elapsed time,
--- cpu time, system time, and the maximum resident size (in Kilobytes).
benchCommand :: String -> Benchmark CmdResult
benchCommand cmd = benchmark $ do
  pid <- getPID
  let timefile = ".time" ++ show pid
      timecmd = "/usr/bin/time -q --format=\"BENCHMARKTIME=(%e,%U,%S,%M)\" -o "
                  ++ timefile ++ " " ++ cmd
  --putStrLn $ "TIMECMD: " ++ timecmd
  status <- system timecmd
  bmout <- readCompleteFile timefile
  case reads (extractTimeInOutput bmout) of
    [((etime,ctime,stime,maxmem),_)] -> do
      system $ "rm -f " ++ timefile
      --putStrLn $ "RESULT: " ++ show (CD cmd status etime ctime stime maxmem)
      return (CD cmd status etime ctime stime maxmem)
    _ -> error $ "Cannot read output of time command:\n" ++ bmout
 where
  -- extract benchmark time from timing output:
  extractTimeInOutput =
    tail . snd . break (=='=') . head . filter ("BENCHMARKTIME" `isPrefixOf`)
         . lines

--- Benchmark the elapsed time (in seconds) to execute a shell command.
elapsedTime4Command :: String -> Benchmark Float
elapsedTime4Command = mapBench elapsedTime . benchCommand

--- Benchmark the cpu time (in seconds) to execute a shell command.
cpuTime4Command :: String -> Benchmark Float
cpuTime4Command = mapBench cpuTime . benchCommand

--- Benchmark the execution of a shell command where
--- a maximum time limit for the execution (in seconds) is given.
--- Returns `Nothing`, if the time limit is reached or the command terminated
--- with a non-zero exit code, or `Just` the benchmark results.
benchCommandWithLimit :: String -> Float -> Benchmark (Maybe CmdResult)
benchCommandWithLimit cmd tlimit =
  mapBench (\cd -> if exitStatus cd == 0 then Just cd else Nothing)
           (benchCommand $ "/usr/bin/timeout " ++ show tlimit ++ "s " ++ cmd)


-----------------------------------------------------------------
-- Get system specific infos.
-- The current implementations work for Linux.
-- Other operating system might require other implementations of these
-- operations.

--- Retrieve the host name.
getHostName :: IO String
getHostName = runCmd "hostname"

--- Retrieve the operating system name (e.g., "Linux").
getOS :: IO String
getOS = runCmd "uname -o"

--- Retrieve the operating system description (e.g., "Ubuntu 12.04.3 LTS").
getSystemDescription :: IO String
getSystemDescription = runCmd "lsb_release -s -d"

--- Retrieve the operating system id (e.g., "Ubuntu").
getSystemID :: IO String
getSystemID = runCmd "lsb_release -s -i"

--- Retrieve the operating system release (e.g., "12.04").
getSystemRelease :: IO String
getSystemRelease = runCmd "lsb_release -s -r"

--- Retrieve the number of cores.
--- Implemented by counting the processor entries in /proc/cpuinfo
getCoreNumber :: IO String
getCoreNumber =
  readFile "/proc/cpuinfo" >>=
    return . show . length . filter (\ s -> take 9 s == "processor") . lines

--- Retrieve the model of the CPU (e.g., "Intel(R) Core(TM) i5 CPU...").
--- Implemented by look up the model name in /proc/cpuinfo.
--- The copyright and trademark abbreviations are omitted.
getCPUModel :: IO String
getCPUModel = do
  cpuinfo <- readFile "/proc/cpuinfo"
  let modelnames = filter (\ s -> take 2 (words s) == ["model","name"])
                          (lines cpuinfo)
  return (if null modelnames
          then "???"
          else let (_,mname) = break (==':') (head modelnames)
                in if null mname then "???"
                                 else strip (delCRTM (tail mname)))
 where
  delCRTM s = case s of
    []                 -> []
    '(':'R':')':xs     -> delCRTM xs
    '(':'T':'M':')':xs -> delCRTM xs
    x:xs               -> x : delCRTM xs

-----------------------------------------------------------------
-- Auxiliaries:

--- Run the command and returns stdout output
runCmd :: String -> IO String
runCmd cmd = connectToCommand cmd >>= hGetContents >>= return . strip

--- Remove leading and trailing whitespace
strip :: String -> String
strip = reverse . dropWhile isSpace . reverse . dropWhile isSpace

-----------------------------------------------------------------
