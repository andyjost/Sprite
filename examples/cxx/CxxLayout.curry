-- Member layout of a standard-layout struct, and the search for the member
-- order of the smallest size.
--
-- The layout follows the Itanium C++ ABI for a standard-layout struct without
-- bit-fields, base classes or virtual members: the members are placed in
-- declaration order, each at the next offset that is a multiple of its
-- alignment; the alignment of the struct is the largest alignment of a
-- member; the size is the end of the last member rounded up to that
-- alignment; an empty struct has size 1.  The sizes and alignments are those
-- of CxxType under the LP64 data model of CxxLimits.  A member whose type has
-- no size (void, a function, a class) has no layout.
--
-- The search is non-deterministic.  perm yields one order of the members per
-- value, so an expression over perm means every order at once.  A set
-- function collects the size of every order together with the order, and the
-- smallest size wins.  A constraint on the order is one more rule: a guard on
-- the generated order.

module CxxLayout where

import Control.SetFunctions
import Data.List (minimum, sum)
import CxxType

-- The layout -----------------------------------------------------------------

-- A member of a struct: its name and its type.
type Member = (String, Type)

-- A member with its size and its alignment.  The layout needs nothing else
-- of a member, so the search takes both once, before it permutes.
type Sized = (String, Int, Int)

sized :: Member -> Sized
sized (name, t) = (name, sizeof_ t, alignof_ t)

nameOf :: Sized -> String
nameOf (name, _, _) = name

-- A placed member: its name, its offset, its size and the padding in front
-- of it.
type Placed = (String, Int, Int, Int)

-- A layout: the placed members in order, then the size, the alignment and
-- the padding at the end of the struct.
type Layout = ([Placed], Int, Int, Int)

-- The layout of the members in the given order.
layout :: [Member] -> Layout
layout ms = layoutSized (map sized ms)

layoutSized :: [Sized] -> Layout
layoutSized ss = (placed, size, align, size - end)
  where
    (placed, end) = place 0 ss
    align = foldr max 1 [a | (_, _, a) <- ss]
    size = max 1 (roundUp end align)

-- Places the members from an offset, each at the next multiple of its
-- alignment.  Returns the placed members and the end of the last one.
place :: Int -> [Sized] -> ([Placed], Int)
place off [] = ([], off)
place off ((name, bytes, a) : ss) = (placed : rest, end)
  where
    start = roundUp off a
    placed = (name, start, bytes, start - off)
    (rest, end) = place (start + bytes) ss

-- The smallest multiple of a that is not below n.
roundUp :: Int -> Int -> Int
roundUp n a = ((n + a - 1) `div` a) * a

structSize :: Layout -> Int
structSize (_, size, _, _) = size

-- The bytes of padding in a layout, between the members and at the end.
padding :: Layout -> Int
padding (placed, size, _, _) = size - sum [bytes | (_, _, bytes, _) <- placed]

-- The search -----------------------------------------------------------------

-- One order of a list; every order at once.  Both rules of insert apply to a
-- non-empty list, so each call is a choice.
perm :: [a] -> [a]
perm []     = []
perm (x:xs) = insert x (perm xs)

insert :: a -> [a] -> [a]
insert x ys     = x : ys
insert x (y:ys) = y : insert x ys

-- The size of one order of the members, with the order.  The set function
-- (set1 sizeOfOrder) collects the pair of every order.
sizeOfOrder :: [Sized] -> (Int, [Sized])
sizeOfOrder ss = (structSize (layoutSized order), order)
  where order = perm ss

-- The same with one more rule: the named member stays first.  The guard
-- tests the head of the order.  An order with another member first fails,
-- and a failure is not a value of the set.
sizeOfOrderFirst :: String -> [Sized] -> (Int, [Sized])
sizeOfOrderFirst first ss | nameOf (head order) == first = (size, order)
  where (size, order) = sizeOfOrder ss

-- The result of a search: the number of orders searched, the number of them
-- that reach the smallest size, and the layout of the first of those in the
-- order of the names.
type Search = (Int, Int, Layout)

-- The smallest size over every order of the members.
smallest :: [Member] -> Search
smallest ms = summarize (set1 sizeOfOrder (map sized ms))

-- The smallest size over the orders with the named member first.
smallestWithFirst :: String -> [Member] -> Search
smallestWithFirst first ms =
  summarize (set2 sizeOfOrderFirst first (map sized ms))

-- Sorts the pairs by size.  The run of the smallest size starts the list;
-- minimum picks the first of those orders in the order of the names, which
-- are unique.  No value for an empty set.
summarize :: Values (Int, [Sized]) -> Search
summarize pairs = (length bySize, length best, layoutSized (minimum best))
  where
    bySize = sortValuesBy (\p q -> fst p <= fst q) pairs
    best = [order | (size, order) <- bySize, size == fst (head bySize)]
