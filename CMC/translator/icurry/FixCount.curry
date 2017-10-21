module FixCount where

import ICurry

execute (IModule _ _ _ funct_list)
  | map fixFunct funct_list =:= _
  = success

fixFunct (IFunction _ _ stmt_list)
  = foldl fixStmt (1 + start) stmt_list
  where start = countStmtList stmt_list

-- There are no nested cases in any of these
fixStmt c (IExternal _) = c
fixStmt c (Comment _) = c
fixStmt c (Declare _) = c
fixStmt c (Assign _ _) = c
fixStmt c (Fill _ _ _) = c
fixStmt c (Return _) = c
-- There could be nested cases in the branches
fixStmt c (ATable c _ _ branch_list) 
  = foldl fixStmt (c+1) (concatMap snd branch_list)
  --  = foldl (\ n ss -> foldl fixStmt n ss) c (map snd branch_list)
fixStmt c (BTable c _ _ branch_list)
  = foldl fixStmt (c+1) (concatMap snd branch_list)

------------------------------------------------------------------
-- Find the maximum index of a variable by a traversal of a function

countStmtList [] = 0
countStmtList (s:ss) = max (countStmt s) (countStmtList ss)

-- There are no nested cases in any of these
countStmt (IExternal _) = 0
countStmt (Comment _) = 0
countStmt (Declare (Variable _ _)) = 0
countStmt (Assign _ _) = 0
countStmt (Fill _ _ _) = 0
countStmt (Return _) = 0
-- There could be nested cases in the branches
countStmt (ATable _ _ _ branch_list) 
  = countStmtList (concatMap snd branch_list)
countStmt (BTable _ _ _ branch_list)
  = countStmtList (concatMap snd branch_list)
