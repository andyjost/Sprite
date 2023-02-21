-- Test to simulate the structure of the libraries GUI/HTML libraries
-- w.r.t. the instantiation of free variables.

-- create environment with n free variables:
createEnv :: Int -> [(String,Int)]
createEnv n = if n==0 then [] else (_,n) : createEnv (n-1)

-- instantiate free variables in environment
numberVars :: String -> [(String,Int)] -> [(String,Int)]
numberVars prefix env = numberVarsFrom 0 env
 where
  numberVarsFrom _ [] = []
  numberVarsFrom i ((lvar,n):env)
    | lvar =:= prefix++show i
    = (lvar,n) : numberVarsFrom (i+1) env

-- Lookup in the environment with a variable:
getRefVal :: [(String,Int)] -> String -> Int
getRefVal env ref = maybe 0 id (lookup ref env)

-- Main program: create an environment with free variables as indices,
-- instantiate the free variables, and look up all associated values
main prefix n = do
  let env  = createEnv n
      refs = map fst env
  print (numberVars prefix env)
  print (foldr (+) 0 (map (getRefVal env) refs))

main1 = main ""       100
main2 = main "XXX"    100
main3 = main "XXXYYY" 100
main4 = main ""       200
main5 = main "XXX"    200
main6 = main "XXXYYY" 200

{-
Results for KiCS2 on lafite:

main 100, only show i: 0.56
main 200, only show i: 6.52
main 100, show i++"XXX": 0.68
main 200, show i++"XXX": 7.02
main 100, show i++"XXXYYY": 0.77
main 200, show i++"XXXYYY": 7.23
main 100, "XXX"++show i: 3.25
main 200, "XXX"++show i: 27.56
main 100, "XXXYYY"++show i: 6.00
main 200, "XXXYYY"++show i: 49.64
main 100, "XXXYYYZZZ"++show i: 8.84

Results for PAKCS on lafite:

main 100, only show i: 0.03
main 200, only show i: 0.10
main 100, show i++"XXX": 0.40
main 200, show i++"XXX": 0.10
main 100, show i++"XXXYYY": 0.05
main 200, show i++"XXXYYY": 0.11
main 100, "XXX"++show i: 0.07
main 200, "XXX"++show i: 0.21
main 100, "XXXYYY"++show i: 0.10
main 200, "XXXYYY"++show i: 0.32

-}
