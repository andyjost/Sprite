-- Programs for unit_cxx_runtime.py.
module CxxRuntime where

-- Allocates nodes without bound.  lastOf walks the list by a tail call, and
-- head xs holds the first cell, so every cell stays reachable and the
-- collector reclaims nothing.  The process runs out of memory.
unbounded :: Int
unbounded = lastOf xs + head xs where xs = [1..]

lastOf :: [Int] -> Int
lastOf (x:xs) = if null xs then x else lastOf xs

-- Writes a line.  sprite-exec then prints the value, ().
main :: IO ()
main = putStrLn "Hello from Curry"
