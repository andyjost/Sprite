module MacroBodies where

import List
import ICurry
import Block
import Utils
import XFormat
import MacroStatement

macro_body qname _ stmt_list
  = case stmt_list of
      [IExternal string] -> macro_body_external qname string
      _                  -> macro_body_internal qname stmt_list

macro_body_external (_,name) string
  = Block 0 [
      NL,
      SLine (format "// external Node* %s::hfun() { throw \"External \\\"%s\\\" not implemented\"; }" 
      [FS (translate name), FS string])
    ]

macro_body_internal (_,name) stmt_list
  = Block 0 [
      NL,
      SLine (format "Node* %s::hfun() { // %s" [FS (translate name), FS name]),
      Block 1 (map makeStmt stmt_list),
      SLine "}"
    ]
