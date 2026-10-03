-- Typed expressions at the root of a rule.  icurry 3.1.0 drops the bindings
-- of a let or free declaration under such a type annotation; the port copies
-- that output unless icurry compatibility is switched off.
module TypedRoot where

typedLetRoot :: Int -> Int
typedLetRoot n = (let k = n + 1 in k * k) :: Int

typedFreeRoot :: Int -> Int
typedFreeRoot n = (let x free in x =:= n &> x) :: Int

typedOrRoot :: Int -> Int
typedOrRoot n = (n ? succ n) :: Int

typedCallRoot :: Int -> Int
typedCallRoot n = (succ n :: Int)

typedNested :: Int -> Int
typedNested n = succ ((let k = n + 1 in k * k) :: Int)
