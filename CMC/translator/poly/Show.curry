-- Extend an ICurry module with some new functions.
-- There is a new function for each type.
-- For a type t, the new function is the generic show of t.
-- The name of the new function is modname.show.t 
-- For a polymorphic type t x, the generic show of x is Prelude.show

import ICurry
import Fix

-- the name of the show function for a given typename
xshow typename = "show."++typename
primitive typename = "primitive."++xshow typename

NEW = _

execute (IModule modname {-imported_list-}_ data_list {-funct_list-}_)
  = concat [make_funct modname onetype | onetype <- data_list]

-- built-in type, no constructors are declared
make_funct modname (t@(_,typename),[])
  = [IFunction qname 1 
        [Declare (Variable 1 (ILhs (qname,1))),
         ATable 1 False (Reference 1)
             [(IConstructor t 1, 
              [Return (Applic False ename [Reference 1])])]]]
  where qname = (modname, xshow typename)
        ename = (modname, primitive typename)

-- algebraic type, some constructors are declared
make_funct modname ((_,typename),clist@(_:_))
  | fixBody 2 body =:= _    -- fix the identifiers of the variables
  = [IFunction qname 2 (Declare (Variable 1 (ILhs (qname,1))) : body)]
  where qname = (modname, xshow typename)
        body = make_body modname clist

make_body modname clist 
   = [ATable 1 False (Reference 1) [(r, make_entry modname r) | r <- clist]]

-- one case of a table
make_entry modname (IConstructor qname arity)
  = declare ++ loop seed init_vars
  where -- TODO: why do I need prim_label when I have the name ???
        seed = Applic False ("Prelude","prim_label") [Reference 1]
        init_vars = [Variable NEW (IVar 1 (qname,k)) | k <- [1..arity]]
        declare = [Declare v | v <- init_vars]
        loop new_seed [] = [Return new_seed]
        loop new_seed (Variable k _ : vars) =
            loop (Applic True ("Prelude",":") 
                    [BuiltinVariant (Bchar '(')
                    ,Applic False ("Prelude","++") 
                        [new_seed
                        ,Applic False ("Prelude","++") 
                            [Applic True ("Prelude",":") 
                               [BuiltinVariant (Bchar ' ')
                               ,Applic True ("Prelude","[]") []]
                            ,Applic False ("Prelude","++") 
                                [Applic False (modname,"show") [Reference k]
                                ,Applic True ("Prelude",":") 
                                    [BuiltinVariant (Bchar ')')
                                    ,Applic True ("Prelude","[]") []]]]]]) vars