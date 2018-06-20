-- {-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}

import ICurry
import JSON
import Float

xclass x = ("__class__", JS x)
xexpr x = ("expr", toExpr x)
fullname (mod,ident) = mod++"."++ident
jint x = JN (i2f x)
jbool True = JTrue
jbool False = JFalse

icurryToJson (IModule name imported_list data_list funct_list) =
  JA [             -- an array allows for multiple modules in a JSON file
     JO [ xclass "IModule"
        , ("name", JS name)
        , ("imports", JA (map JS imported_list))
        , ("types", JA (map toData data_list))
        , ("functions", JA (map toFunction funct_list))
        ]
     ]

toData (qname, clist) =
  JA [ JS (fullname qname)
     , JA (map toConstructor clist)
     ]

toConstructor (IConstructor qname arity) =
  JO [ xclass "IConstructor"
     , ("ident", JS (fullname qname))
     , ("arity", jint arity)
     ]

toFunction (IFunction qname arity stmt_list) =
  JO [ xclass "IFunction"
     , ("ident", JS (fullname qname))
     , ("arity", jint arity)
     , ("code", JA (map toStmt stmt_list))
     ]

------------------------------------------------------------------
-- Statements
toStmt :: ICurry.Statement -> JSON.Json

toStmt (Declare (Variable id scope)) =
  JO [ xclass "Declare"
     , ("var", JO
       [ xclass "Variable"
       , ("vid", jint id)
       , ("scope", toScope scope)
       ])
     ]

toStmt (IExternal string) =
  JO [ xclass "IExternal"
     , ("ident", JS string)
     ]

toStmt (Comment string) =
  JO [ xclass "Comment"
     , ("text", JS string)
     ]

toStmt (Assign i expr) =
  JO [ xclass "Assign"
     , ("vid", jint i)
     , xexpr expr
     ]

toStmt (Fill i path j) =
  JO [ xclass "Fill"
     , ("v1", jint i)
     , ("path", JA (map toPath path))
     , ("v2", jint j)
     ]
  where toPath (qname, index) =
          JO [ xclass "Successor"
             , ("headsymbol", JS (fullname qname))
	           , ("position", jint index)
	           ]

toStmt (Return expr) =
  JO [ xclass "Return"
     , xexpr expr
     ]

toStmt (ATable suffix flex expr branch_list) =
  JO [ xclass "ATable"
     , ("counter", jint suffix)
     , ("isflex", jbool flex)
     , xexpr expr
     , ("switch", JA (map toABranch branch_list))
     ]
  where toABranch (IConstructor qname arity, stmt_list) =
          JA [ JS (fullname qname)
             , JA (map toStmt stmt_list)
             ]

toStmt (BTable suffix flex expr branch_list) =
  JO [ xclass "BTable"
     , ("counter", jint suffix)
     , ("isflex", jbool flex)
     , xexpr expr
     , ("switch", JA (map toBBranch branch_list))
     ]
  where toBBranch (biv, stmt_list) =
          JA [ toVariant biv
             , JA (map toStmt stmt_list)
             ]

------------------------------------------------------------------
-- Scopes
toScope :: ICurry.VarScope -> JSON.Json

toScope (ILhs (qname, index)) =
  JO [ xclass "ILhs"
     , ("index", JA [ JS (fullname qname), jint index ])
     ]
toScope (IVar i (qname, j)) =
  JO [ xclass "IVar"
     , ("vid", jint i)
     -- proposal by analogy with ILhs
     , ("index", JA [ JS (fullname qname), jint j ])
     ]
toScope IBind =
  JO [ xclass "IBind"
     ]
toScope IFree =
  JO [ xclass "IFree"
     ]

------------------------------------------------------------------
-- Expressions

toExpr Exempt =
  JO [ xclass "Exempt"
     ]

toExpr (Reference i) =
  JO [ xclass "Reference"
     , ("vid", jint i)
     ]

toExpr (BuiltinVariant biv) = toVariant biv

toExpr (Applic constr qname expr_list) =
  JO [ xclass "Applic"
     , ("ident", JS (fullname qname))
     , ("args", JA (map toExpr expr_list))
     ]

toExpr (PartApplic missing expr) =
  JO [ xclass "PartApplic"
     , ("missing", jint missing)
     , xexpr expr
     ]

toExpr (IOr arg1 arg2) =
  JO [ xclass "IOr"
     , ("lhs", toExpr arg1)
     , ("rhs", toExpr arg2)
     ]

toVariant (Bint int)     = JO [ xclass "Applic"
                              , ("ident", JS (fullname ("Prelude", "Int")))
                              , ("args", JA [jint int])
                              ]
toVariant (Bfloat float) = JO [ xclass "Applic"
                              , ("ident", JS (fullname ("Prelude", "Float")))
                              , ("args", JA [JN float])
                              ]
toVariant (Bchar char)   =
  let charval = case char of
       '\t' -> "\\t"
       '\b' -> "\\b"
       '\n' -> "\\n"
       '\r' -> "\\r"
       '\f' -> "\\f"
       '\'' -> "\\'"
       '\"' -> "\\\""
       '\\' -> "\\\\"
       _    -> [char]
  in JO [ xclass "Applic"
        , ("ident", JS (fullname ("Prelude", "Char")))
        , ("args", JA [JS charval])
        ]

{-
https://docs.oracle.com/javase/tutorial/java/data/characters.html

\t 	Insert a tab in the text at this point.
\b 	Insert a backspace in the text at this point.
\n 	Insert a newline in the text at this point.
\r 	Insert a carriage return in the text at this point.
\f 	Insert a formfeed in the text at this point.
\' 	Insert a single quote character in the text at this point.
\" 	Insert a double quote character in the text at this point.
\\ 	Insert a backslash character in the text at this point.
-}
