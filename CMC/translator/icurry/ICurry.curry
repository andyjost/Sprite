-- Same as Flatcurry QName
type IName = (String,String)

-- Same as FlatCurry Literal
data BuiltinVariant
  = Bint   Int
  | Bfloat Float
  | Bchar  Char

data IModule 
  = IModule
    String                      -- this module name
    [String]                    -- imported modules names
    [(IName,[IConstructor])]    -- constructors grouped by type
    [IFunction]                 -- functions

data IConstructor
  = IConstructor 
    IName    -- qualified FLP name
    Int      -- arity

data IFunction
  = IFunction
    IName               -- qualified FLP name
    Int                 -- arity
    [Statement]         -- function body

-- A variable identifies a node in an expression called "context of
-- the variable".  For example in
-- 
--     f (x:xs) = case xs++[x] of
--          [] -> 0
--          (u:us) -> u - f us
-- 
-- the context of x and xs is the (match of the) left-hand side.
-- The context of u and us is the case selector.
--
-- There are several flavors of variables, see comments in the code.
--
-- In the representation, the integer is a unique identifier, the
-- token tells which is the context of the variable.

type Successor = (IName,Int)
data VarScope 
  = ILhs Successor -- argument of the match of a left-hand side
  -- obsolete | ICase          -- selector of a case (local variable)
  | IVar Int Successor   -- argument of another variable
  | IBind          -- local, possibly shared subexpression
  | IFree          -- free variable
data Variable = Variable Int VarScope

data Expression
  = Exempt
  | Reference Int
  | BuiltinVariant BuiltinVariant
  -- True applies a constructor, False an operation
  | Applic Bool IName [Expression] 
  | PartApplic Int Expression
  -- This is produced by overlapping rules
  | IOr Expression Expression

data Statement
  = IExternal String         -- TODO: where is this used ???
  | Comment String
  | Declare Variable
  | Assign Int Expression
  -- Fill v1 p v2 means replace the node of v1 at p with v2
  -- where v1 and v2 are indexes of variables and p a path in v1.
  | Fill Int [Successor] Int
  | Return Expression
  | ATable Int Bool Expression [(IConstructor,[Statement])]
  | BTable Int Bool Expression [(BuiltinVariant,[Statement])]  
