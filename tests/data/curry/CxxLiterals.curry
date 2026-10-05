-- Programs for unit_cxx_literals.py: the shared literal nodes of the C++
-- backend.
module CxxLiterals where

-- Literals from the tables of the runtime.  After one step the successors
-- of the pair are the shared nodes.
small :: (Int, Char)
small = (7, 'a')

-- Literals outside the tables: nodes of the module, made once at load.
large :: (Int, Char, Float)
large = (100000, '\955', 2.5)

-- The same large literal elsewhere in the module: one node serves both.
largeAgain :: (Int, Int)
largeAgain = (100000, 0)

-- The last integer of the table and the first outside it.  (A negative
-- literal is negate applied to a positive one in ICurry, so none is spelled
-- here.)
bounds :: [Int]
bounds = [1023, 1024]

-- Equality and ordering through shared and unshared nodes.
eqs :: [Bool]
eqs = [1 == 1, 1 == 2, 'a' == 'a', 'a' < 'b', (1, 1) == (1, 1)
      , 100000 == 100000, 1024 == 1024, 2.5 == 2.5]

-- A unification with a literal binds the variable to a shared node.
unify :: Int
unify = let x free in x =:= 1 &> x + 1

-- Narrowing on literal patterns: the value bindings hold the shared nodes.
narrow :: Int -> Int
narrow 1 = 10
narrow 2 = 20

narrowed :: (Int, Int)
narrowed = let x free in (narrow x, x)

-- A loop that spells the literals 0 and 1 in every step.  countDown n is 0
-- after n steps.  The literals cost no allocation.
countDown :: Int -> Int
countDown n = if n == 0 then 0 else countDown (n - 1)

-- A string of literal characters, inside and outside the table.
greeting :: String
greeting = ['h', 'i', '!', '\955']

-- One shared node twice in a value.
twice :: (Int, Int)
twice = (1, 1)
