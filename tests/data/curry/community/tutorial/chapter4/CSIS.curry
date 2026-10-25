import Data.List
import Control.Search.SetFunctions

-- Prerequisites table, 2001 catalog
-- This is a directed acyclic graph

isPrereqOf :: Int -> Int
isPrereqOf 162 = 161
isPrereqOf 163 = 162
isPrereqOf 200 = 162
isPrereqOf 201 = 200
isPrereqOf 202 = 163
isPrereqOf 202 = 201
isPrereqOf 250 = 163
isPrereqOf 251 = 250
isPrereqOf 252 = 251
isPrereqOf 300 = 202
isPrereqOf 301 = 252
isPrereqOf 301 = 300
isPrereqOf 302 = 301
isPrereqOf 303 = 252
isPrereqOf 303 = 300
isPrereqOf 350 = 252

isPrereqOf'set :: Int -> Values Int
isPrereqOf'set course = set1 isPrereqOf course

-- Tree of prereqs.  Local to transClosPrereq only.
-- The children of a node are the direct prerequisites of the decoration.
data Tree = Tree Int [Tree]

-- Transitive closure of prerequisite of a course c,
-- i.e., all the courses you have to take before taking c.
transClosPrereq :: Int -> [Int]
transClosPrereq course = (nub . tail . collect . grow) course
  where
      -- Grow the prerequisites tree.
      -- It terminates because the graph is acyclic
      grow course = Tree course children
          where roots = (sortValues . isPrereqOf'set) course
                children = map grow roots

      -- Collect all the prerequisites of the root.
      -- Some prereqs may occur repeatedly.
      collect (Tree course children) = course : concatMap collect children

main = transClosPrereq 202  -- -> [163,162,161,201,200]

------------------------------------------------------------------

-- isPrereqOf is a many-to-many relation.
-- The inverse of isPrereqOf is meaningfull in its own right

giveAccessTo :: Int -> Int
giveAccessTo (isPrereqOf x) = x

test1 = giveAccessTo 162
test2 = set1 giveAccessTo 162
