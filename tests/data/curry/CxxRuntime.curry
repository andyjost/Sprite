-- Programs for unit_cxx_runtime.py.
module CxxRuntime where

-- Allocates nodes without bound and without nesting evaluations: lastOf
-- walks the list by a tail call.  The collector does not run before one
-- billion nodes exist, so the process runs out of memory first.
unbounded :: Int
unbounded = lastOf [1..]

lastOf :: [Int] -> Int
lastOf (x:xs) = if null xs then x else lastOf xs

-- Writes a line.  sprite-exec then prints the value, ().
main :: IO ()
main = putStrLn "Hello from Curry"
