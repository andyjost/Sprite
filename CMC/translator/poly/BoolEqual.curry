-- Extend an ICurry module with some new functions.
-- There is a new function for each type.
-- For a type t, the new function is the Boolean equality of t.
-- The name of the new function is modname.==.t 
-- For a polymorphic type t x, the equality of x is Prelude.==

import ICurry
import Fix

-- the name of the equal function for a given typename
equals typename = "==."++typename
primitive typename = "primitive."++equals typename

NEW = _

execute (IModule modname {-imported_list-}_ data_list {-funct_list-}_)
  = concat [make_funct modname onetype | onetype <- data_list]

-- built-in type, no constructors are declared
make_funct modname ((_,typename),[])
  = [IFunction qname 2 
       [Declare (Variable 1 (ILhs (qname,1))), 
        Declare (Variable 2 (ILhs (qname,2))),
        ATable 1 False (Reference 1)
           [((IConstructor (modname,typename) 1),
               [ATable 2 False (Reference 2)
                   [((IConstructor (modname,typename) 1),
                         [Return (Applic False ename
                              [Reference 1, Reference 2])])]])]],
     IFunction ename 2
        [(IExternal (modname++"."++primitive typename))]]
  where qname = (modname, equals typename)
        ename = (modname, primitive typename)

-- algebraic type, some constructors are declared
make_funct modname ((_,typename),clist@(_:_))
  | fixBody 3 body =:= _    -- fix the identifiers of the variables
  = [IFunction qname 2 (declare ++ body)]
  where qname = (modname, equals typename)
        var_1 = Variable 1 (ILhs (qname,1))
        var_2 = Variable 2 (ILhs (qname,2))
	declare = [Declare var_1, Declare var_2]
        body = make_body clist

make_body clist = [ATable 1 False (Reference 1)
                      [(q, [ATable k False (Reference 2)
                         [make_entry q r | r <- clist]])
                             | (k,q) <- zip [2..] clist]]

-- one case of a table
make_entry q r 
  | q == r = (r, make_recur r var_list)
  | otherwise = (r, [Return (Applic True ("Prelude","False") [])])
  where var_list = make_var_list r

-- all the variables of one case of a table
make_var_list :: IConstructor -> [[Variable]]
make_var_list (IConstructor qname arity)
  | arity == 0 = []
  | otherwise = [[Variable NEW (IVar 1 (qname,k)),
                  Variable NEW (IVar 2 (qname,k))] | k <- [1..arity]]

-- the entire body (declarations + returned expression) of one case of a table
make_recur :: IConstructor -> [[Variable]] -> [Statement]
make_recur (IConstructor _ arity) var_list
  | arity == 0 = [Return (Applic True ("Prelude","True") [])]
  | otherwise = declare ++ [Return (merge subexprs)]
  where subexprs = [Applic False ("Prelude","==") [Reference v, Reference w]
                      | [Variable v _, Variable w _] <- var_list]
        merge [v] = v
        merge (v1:v2:vs) = Applic False ("Prelude","&&") [v1, merge (v2:vs)]
        declare = concat [[Declare x, Declare y] | [x,y] <- var_list]
