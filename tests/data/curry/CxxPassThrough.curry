-- Programs for unit_cxx_passthrough.py: arguments that a step only passes
-- on, which the C++ backend reads as plain pointers (passthrough.py).
module CxxPassThrough where

import Control.SetFunctions

data T3 = T3 Int Int Int

-- Every argument is passed on, in another order.
rot3 :: Int -> Int -> Int -> (Int, Int, Int)
rot3 x y z = (z, x, y)

-- An argument returned as it is: the redex takes a copy of a primitive
-- value, and is forwarded to any other node.
second :: Int -> Int -> Int
second _ y = y

-- An argument passed on to a call and to a partial application.
twiceOver :: Int -> [Int]
twiceOver x = map (plus x) [x, 1]

plus :: Int -> Int -> Int
plus a b = a + b

-- An argument passed on to both sides of a choice.
orPass :: Int -> Int -> Int
orPass x y = x ? y

-- A pattern variable passed on: the match reads it from the matched node.
firstOf :: T3 -> Int
firstOf (T3 a _ _) = a

-- A result larger than its redex: the redex is forwarded, so every other
-- slot that holds it holds a forward node afterwards.
big :: Int -> T3
big n = T3 n n n

keep :: Int -> T3 -> (Int, T3)
keep u v = (u, v)

-- keep reads a slot that holds a forward node: seq evaluated b first.
fwdInSlot :: Int -> (Int, T3)
fwdInSlot x = let b = big x in firstOf b `seq` keep (firstOf b) b

-- A recursive let: the first cell refers to the second before it exists.
cyc :: Int -> [Int]
cyc n = let xs = n : ys
            ys = (n + 1) : xs
        in take 5 xs

-- A let that names an argument.
aliasPass :: Int -> (Int, Int)
aliasPass x = let y = x in (y, x)

-- A free variable beside a plain argument.
withFree :: Int -> Int
withFree x = y =:= x &> y where y free

headPlus :: [Int] -> Int
headPlus (x:_) = x + 1

plainHead :: Int
plainHead = headPlus [41]

-- Inside a set function the argument sits behind a set guard.  A function
-- that passes it on must keep the guard: a choice in the argument is
-- outside the set function, so the goal has two values, one set each.
addOne :: Int -> Int
addOne x = x + 1

passOn :: Int -> Int
passOn x = addOne x

passOn2 :: Int -> Int
passOn2 x = passOn x

setPass :: [Int]
setPass = sortValues (set1 passOn (1 ? 2))

setPass2 :: [Int]
setPass2 = sortValues (set1 passOn2 (1 ? 2))

-- A choice made inside the set function stays inside: one set.
innerChoice :: Int -> Int
innerChoice x = addOne x ? addOne (addOne x)

setInner :: [Int]
setInner = sortValues (set1 innerChoice 5)

-- The argument passed on into the value.
wrapIt :: Int -> Maybe Int
wrapIt x = Just x

setWrap :: [Maybe Int]
setWrap = sortValues (set1 wrapIt (1 ? 2))

-- A pattern variable under the guard of the argument: the guard crossed by
-- the match is kept.
setHead :: [Int]
setHead = sortValues (set1 headPlus [1 ? 2])

-- The choice is in a cell built inside the set function: one set.
consInside :: Int -> Int
consInside x = headPlus [x ? x + 1]

setCons :: [Int]
setCons = sortValues (set1 consInside 1)
