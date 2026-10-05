-- Programs for unit_cxx_emit.py: a case whose default branch body is a bare
-- literal or a nullary constructor (issue #59).  The front end completes
-- such a case: the body of the default branch goes into a let variable, and
-- every branch it stands for returns the variable.  The case itself is
-- lifted into a function that takes the variable as an argument.  So the
-- C++ emitter assigns the variable from the spelling of the node: false_(),
-- int_(2), char_(U'z'), a literal node or a partial node of the module, or
-- Node::create(...).
module CxxEmit where

data Type = Int | Char | Ptr Type | Ref Type | Fun Type Type

data Color = Red | Green | Blue

-- A Bool default: a pinned constructor, false_().
isPtr :: Type -> Bool
isPtr t = case t of
  Ptr _ -> True
  _     -> False

-- An Int default from the tables of the runtime: int_(2).
rank :: Type -> Int
rank t = case t of
  Int  -> 0
  Char -> 1
  _    -> 2

-- A Char default: char_(U'z').
code :: Type -> Char
code t = case t of
  Int -> 'i'
  _   -> 'z'

-- A nullary constructor of a user type: Node::create(&Green).
paint :: Type -> Color
paint t = case t of
  Int -> Red
  _   -> Green

-- A literal default inside a nested case.  Both cases are completed, and
-- each lifted function binds a default of its own.
nested :: Type -> Type -> Int
nested t u = case t of
  Ptr _ -> case u of
    Int -> 10
    _   -> 11
  _ -> 12

-- An Int default outside the tables: a literal node of the module.
big :: Type -> Int
big t = case t of
  Int -> 1
  _   -> 100000

-- A Float default: a literal node of the module.
scale :: Type -> Float
scale t = case t of
  Int -> 1.5
  _   -> 2.5

-- An empty list as the default: nil().
elems :: Type -> [Int]
elems t = case t of
  Int -> [1]
  _   -> []

-- A function as the default: a partial node of the module.
step :: Type -> Int -> Int
step t = case t of
  Int -> succ
  _   -> pred

stepped :: Type -> Int -> Int
stepped t n = step t n
