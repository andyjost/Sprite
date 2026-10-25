-- This is a "benchmark" just to show some information
-- about the Curry distribution

import Distribution

-- Prints some infos about the Curry run-time system.
runtimeSystem :: IO ()
runtimeSystem =
  putStrLn $ curryRuntime ++
  " Vers. " ++ show curryRuntimeMajorVersion ++ "." ++ show curryRuntimeMinorVersion

