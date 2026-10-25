module SatSolver where




data Boolean
  = Var Int
  | Yes
  | No
  | Not Boolean
  | And Boolean Boolean
  | Or Boolean Boolean

data Literal = Pos Int | Neg Int

literalVar :: Literal -> Int
literalVar (Pos n) = n
literalVar (Neg n) = n

invLiteral :: Literal -> Literal
invLiteral (Pos n) = Neg n
invLiteral (Neg n) = Pos n

isPositiveLiteral :: Literal -> Bool
isPositiveLiteral (Pos _) = True
isPositiveLiteral (Neg _) = False

type CNF     = [Clause]
type Clause  = [Literal]

booleanToCNF :: Boolean -> CNF
booleanToCNF
  = mapMaybe (simpleClause . map literal . disjunction)
  . conjunction
  . asLongAsPossible distribute
  . asLongAsPossible pushNots
  . asLongAsPossible elim
 where
  elim b = case b of
             Not Yes   -> Just No
             Not No    -> Just Yes
             And No  _ -> Just No
             And Yes x -> Just x
             And _ No  -> Just No
             And x Yes -> Just x 
             Or Yes _  -> Just Yes
             Or No x   -> Just x
             Or _ Yes  -> Just Yes
             Or x No   -> Just x
             _         -> Nothing

  pushNots b = case b of
                 Not (Not x)   -> Just x
                 Not (And x y) -> Just (Or (Not x) (Not y))
                 Not (Or x y)  -> Just (And (Not x) (Not y))
                 _             -> Nothing

  distribute b = case b of
                   Or x (And y z) -> Just (And (Or x y) (Or x z))
                   Or (And x y) z -> Just (And (Or x z) (Or y z))
                   _              -> Nothing

  literal (Var x)       = Pos x
  literal (Not (Var x)) = Neg x

simpleClause :: Clause -> Maybe Clause
simpleClause = liftM (map lit) . foldl add (Just [])
 where
  lit (x,True)  = Pos x
  lit (x,False) = Neg x

  add mm l =
    mm >>- \m ->
    let x = literalVar l; kind = isPositiveLiteral l
    in maybe (Just ((x,kind):m))
             (\b -> if b==kind then Nothing else Just m)
             (lookup x m)

liftM f = maybe Nothing (Just . f)

conjunction :: Boolean -> [Boolean]
conjunction b = flat b []
 where flat c = case c of
                  Yes     -> id
                  And x y -> flat x . flat y
                  _       -> (c:)

disjunction :: Boolean -> [Boolean]
disjunction b = flat b []
 where flat c = case c of
                  No     -> id
                  Or x y -> flat x . flat y
                  _      -> (c:)

asLongAsPossible :: (Boolean -> Maybe Boolean) -> Boolean -> Boolean
asLongAsPossible f = everywhere g
 where g x = maybe x (everywhere g) (f x)

everywhere :: (Boolean -> Boolean) -> Boolean -> Boolean
everywhere f = f . atChildren (everywhere f)

atChildren :: (Boolean -> Boolean) -> Boolean -> Boolean
atChildren f b = case b of
                   Not x   -> Not (f x)
                   And x y -> And (f x) (f y)
                   Or x y  -> Or (f x) (f y)
                   _       -> b

type Bindings = [(Int,Bool)]

data SatSolver = SatSolver CNF Bindings

clauses :: SatSolver -> CNF
clauses (SatSolver cs _) = cs

withClauses :: SatSolver -> CNF -> SatSolver
withClauses (SatSolver _ bs) cs = SatSolver cs bs

bindings :: SatSolver -> Bindings
bindings (SatSolver _ bs) = bs

newSatSolver :: SatSolver
newSatSolver = SatSolver [] []

isSolved :: SatSolver -> Bool
isSolved = null . clauses

lookupVar :: Int -> SatSolver -> Maybe Bool
lookupVar name = lookup name . bindings

assertTrue :: Boolean -> SatSolver -> SatSolver
assertTrue formula solver = simplify (solver `withClauses` newClauses)
 where newClauses = foldl (addClause (bindings solver))
                          (clauses solver)
                          (booleanToCNF formula)

branchOnVar :: Int -> SatSolver -> SatSolver
branchOnVar name solver =
  maybe (branchOnUnbound name solver)
        (const solver)
        (lookupVar name solver)

selectBranchVar :: SatSolver -> Int
selectBranchVar = literalVar . head . head . mergeSort shorter . clauses

solve :: SatSolver -> SatSolver
solve solver
  | isSolved solver = solver
  | otherwise       = solve (branchOnUnbound (selectBranchVar solver) solver)

addClause :: Bindings -> [Clause] -> Clause -> [Clause]
addClause binds oldClauses newClause =
  maybe oldClauses
        (\lits -> if null lits then failed else lits:oldClauses)
        (foldl (addUnbound binds) (Just []) newClause)

addUnbound :: Bindings -> Maybe Clause -> Literal -> Maybe Clause
addUnbound binds mlits lit =
  mlits >>- \lits ->
  maybe (Just (lit:lits))
        (\b -> if b == isPositiveLiteral lit then Nothing else Just lits)
        (lookup (literalVar lit) binds)

updateSolver :: CNF -> Bindings -> SatSolver -> SatSolver
updateSolver cs bs solver =
  SatSolver cs (foldr (uncurry insertBinding) (bindings solver) bs)

insertBinding :: Int -> Bool -> Bindings -> Bindings
insertBinding name newValue bs =
  maybe ((name,newValue):bs)
        (\oldValue ->  if oldValue == newValue then bs else failed)
        (lookup name bs)

simplify :: SatSolver -> SatSolver
simplify solver = updateSolver (fst csNbs) (snd csNbs) solver
 where csNbs = simplifyClauses (clauses solver)

ret x = (x,[])
(x,bs) `bind` f = case f x of (y,bs') -> (y,bs++bs')
tell bs = ((),bs)

simplifyClauses :: CNF -> (CNF,Bindings)
simplifyClauses [] = ret []
simplifyClauses allClauses@(_:_) =
  let shortestClause = head (mergeSort shorter allClauses)
  in if null shortestClause then failed
     else if null (tail shortestClause)
          then propagate (head shortestClause) allClauses `bind` simplifyClauses
          else ret allClauses

propagate :: Literal -> CNF -> (CNF,Bindings)
propagate literal allClauses =
  tell [(literalVar literal, isPositiveLiteral literal)] `bind` \_ ->
  ret (foldr prop [] allClauses)
 where
  prop c cs | literal `elem` c = cs
            | otherwise        = filter (invLiteral literal/=) c : cs

branchOnUnbound :: Int -> SatSolver -> SatSolver
branchOnUnbound name solver = guess (Pos name) solver ? guess (Neg name) solver

guess :: Literal -> SatSolver -> SatSolver
guess literal solver = updateSolver (fst csNbs) (snd csNbs) solver
 where csNbs = propagate literal (clauses solver) `bind` simplifyClauses

shorter :: [a] -> [a] -> Bool
shorter []    _       = True
shorter (_:_) []      = False
shorter (_:xs) (_:ys) = shorter xs ys




--- Bottom-up mergesort.
mergeSort :: (a -> a -> Bool) -> [a] -> [a]
mergeSort leq zs =  mergeLists (genRuns zs)
 where
  -- generate runs of length 2:
  genRuns []               =  []
  genRuns [x]              =  [[x]]
  genRuns (x1:x2:xs) | leq x1 x2 =  [x1,x2] : genRuns xs
                     | otherwise =  [x2,x1] : genRuns xs

  -- merge the runs:
  mergeLists []         =  []
  mergeLists [x]        =  x
  mergeLists (x1:x2:xs) =  mergeLists (merge leq x1 x2 : mergePairs xs)

  mergePairs []         =  []
  mergePairs [x]        =  [x]
  mergePairs (x1:x2:xs) =  merge leq x1 x2 : mergePairs xs


--- Merges two lists with respect to an ordering predicate.

merge :: (a -> a -> Bool) -> [a] -> [a] -> [a]
merge _   [] ys     = ys
merge _   (x:xs) [] = x : xs
merge leq (x:xs) (y:ys) | leq x y   = x : merge leq xs (y:ys)
                        | otherwise = y : merge leq (x:xs) ys



infixl 1 >>-

isJust :: Maybe _ -> Bool
isJust (Just _) = True
isJust Nothing  = False

isNothing :: Maybe _ -> Bool
isNothing Nothing  = True
isNothing (Just _) = False

fromJust :: Maybe a -> a
fromJust (Just a) = a


fromMaybe :: a -> Maybe a -> a
fromMaybe d Nothing  = d
fromMaybe _ (Just a) = a

maybeToList :: Maybe a -> [a]
maybeToList Nothing  = []
maybeToList (Just a) = [a]

listToMaybe :: [a] -> Maybe a
listToMaybe []     = Nothing
listToMaybe (a:_) = Just a
 
catMaybes :: [Maybe a] -> [a]
catMaybes ms = [ m | (Just m) <- ms ]

mapMaybe :: (a -> Maybe b) -> [a] -> [b]
mapMaybe f = catMaybes . map f

--- Monadic bind for Maybe.
--- Maybe can be interpreted as a monad where Nothing is interpreted
--- as the error case by this monadic binding.
--- @param maybeValue - Nothing or Just x
--- @param f - function to be applied to x
--- @return Nothing if maybeValue is Nothing,
---         otherwise f is applied to x
(>>-) :: Maybe a -> (a -> Maybe b) -> Maybe b
Nothing >>- _ = Nothing
(Just x) >>- f  = f x

--- monadic sequence for maybe
sequenceMaybe :: [Maybe a] -> Maybe [a]
sequenceMaybe [] = Just []
sequenceMaybe (c:cs) = c >>- \x -> sequenceMaybe cs >>- \xs -> Just (x:xs)

--- monadic map for maybe
mapMMaybe :: (a -> Maybe b) -> [a] -> Maybe [b]
mapMMaybe f = sequenceMaybe . map f


-----------------------------------------------------------------------------

-- Converts a String in DIMACS CNF format to a CNF,
-- no exception handling is done
{-
dimacsCNF2Boolean :: String -> Boolean
dimacsCNF2Boolean dimCNF =
 let ls = filter (\l -> not (null l
                             || (head l == 'c')
                             || (head l == 'p' )))
                 (lines dimCNF)
 in  foldr1 And (map line2Boolean ls)

  where
  line2Boolean :: String -> Boolean
  line2Boolean line =
    let nums = map read (words line)
    in case nums of
        []  -> Yes
        [_] -> Yes
        _:_ -> foldr1 Or (map num2Boolean (init nums))
  num2Boolean :: Int -> Boolean
  num2Boolean n | n < 0 = Not (Var (abs n))
                | n > 0 = (Var n)
  read :: String -> Int
  read (x:xs) = if  x == '-' then (0-1) * readIter xs 0
                             else readIter (x:xs) 0
  readIter [] res = res
  readIter (x:xs) res = readIter xs (readDigit x + res * 10)
  
  readDigit '0' = 0
  readDigit '1' = 1
  readDigit '2' = 2
  readDigit '3' = 3
  readDigit '4' = 4
  readDigit '5' = 5
  readDigit '6' = 6
  readDigit '7' = 7
  readDigit '8' = 8
  readDigit '9' = 9


init [_] = []
init (x:y:zs) = x: init (y:zs)

abs x | x < 0 = (0-1)*x
      | otherwise = x
-}

main = isSolved (solve (assertTrue testFormula50 newSatSolver))

testFormula50 = (And (Or (Var 46) (Or (Var 39) (Not (Var 17)))) (And (Or (Not (Var 40)) (Or (Var 13) (Var 35))) (And (Or (Not (Var 34)) (Or (Not (Var 32)) (Var 37))) (And (Or (Var 31) (Or (Var 33) (Not (Var 19)))) (And (Or (Not (Var 42)) (Or (Var 39) (Not (Var 20)))) (And (Or (Var 3) (Or (Not (Var 14)) (Not (Var 27)))) (And (Or (Not (Var 15)) (Or (Var 23) (Var 4))) (And (Or (Not (Var 50)) (Or (Not (Var 40)) (Not (Var 48)))) (And (Or (Var 50) (Or (Not (Var 21)) (Var 29))) (And (Or (Not (Var 9)) (Or (Var 20) (Var 40))) (And (Or (Not (Var 16)) (Or (Not (Var 22)) (Var 21))) (And (Or (Not (Var 35)) (Or (Var 6) (Not (Var 27)))) (And (Or (Not (Var 3)) (Or (Not (Var 4)) (Var 23))) (And (Or (Not (Var 47)) (Or (Var 39) (Var 32))) (And (Or (Var 26) (Or (Not (Var 15)) (Not (Var 30)))) (And (Or (Not (Var 23)) (Or (Var 9) (Var 21))) (And (Or (Var 48) (Or (Var 37) (Var 17))) (And (Or (Not (Var 7)) (Or (Not (Var 27)) (Var 24))) (And (Or (Var 40) (Or (Not (Var 23)) (Var 2))) (And (Or (Var 32) (Or (Not (Var 24)) (Var 23))) (And (Or (Not (Var 10)) (Or (Var 12) (Not (Var 25)))) (And (Or (Var 41) (Or (Not (Var 2)) (Not (Var 13)))) (And (Or (Var 28) (Or (Var 33) (Not (Var 13)))) (And (Or (Var 15) (Or (Var 1) (Var 12))) (And (Or (Not (Var 23)) (Or (Var 5) (Var 33))) (And (Or (Not (Var 11)) (Or (Var 25) (Not (Var 32)))) (And (Or (Var 12) (Or (Var 46) (Var 39))) (And (Or (Var 10) (Or (Not (Var 30)) (Var 46))) (And (Or (Var 11) (Or (Var 45) (Not (Var 8)))) (And (Or (Var 30) (Or (Not (Var 33)) (Not (Var 34)))) (And (Or (Var 34) (Or (Var 39) (Not (Var 25)))) (And (Or (Not (Var 2)) (Or (Var 36) (Not (Var 25)))) (And (Or (Not (Var 4)) (Or (Not (Var 19)) (Not (Var 6)))) (And (Or (Var 6) (Or (Var 1) (Not (Var 31)))) (And (Or (Not (Var 43)) (Or (Var 2) (Var 24))) (And (Or (Not (Var 26)) (Or (Var 48) (Var 41))) (And (Or (Var 29) (Or (Var 14) (Var 50))) (And (Or (Not (Var 29)) (Or (Var 6) (Var 28))) (And (Or (Var 21) (Or (Var 11) (Not (Var 19)))) (And (Or (Var 41) (Or (Not (Var 17)) (Var 43))) (And (Or (Var 15) (Or (Var 18) (Var 4))) (And (Or (Var 20) (Or (Not (Var 46)) (Not (Var 29)))) (And (Or (Var 29) (Or (Var 26) (Not (Var 38)))) (And (Or (Not (Var 25)) (Or (Not (Var 30)) (Not (Var 4)))) (And (Or (Not (Var 35)) (Or (Not (Var 21)) (Not (Var 43)))) (And (Or (Not (Var 34)) (Or (Var 50) (Var 3))) (And (Or (Not (Var 3)) (Or (Not (Var 25)) (Var 15))) (And (Or (Not (Var 13)) (Or (Not (Var 22)) (Not (Var 38)))) (And (Or (Not (Var 42)) (Or (Not (Var 2)) (Var 27))) (And (Or (Var 22) (Or (Var 30) (Var 29))) (And (Or (Var 50) (Or (Not (Var 40)) (Var 13))) (And (Or (Not (Var 22)) (Or (Var 29) (Not (Var 42)))) (And (Or (Not (Var 48)) (Or (Var 22) (Not (Var 7)))) (And (Or (Var 32) (Or (Var 13) (Not (Var 37)))) (And (Or (Not (Var 16)) (Or (Not (Var 30)) (Var 11))) (And (Or (Var 7) (Or (Not (Var 44)) (Not (Var 6)))) (And (Or (Not (Var 37)) (Or (Var 17) (Var 11))) (And (Or (Var 13) (Or (Not (Var 1)) (Var 42))) (And (Or (Not (Var 4)) (Or (Not (Var 18)) (Not (Var 26)))) (And (Or (Not (Var 22)) (Or (Not (Var 42)) (Var 13))) (And (Or (Var 49) (Or (Not (Var 43)) (Not (Var 5)))) (And (Or (Not (Var 49)) (Or (Var 11) (Var 47))) (And (Or (Var 40) (Or (Not (Var 14)) (Var 8))) (And (Or (Var 13) (Or (Not (Var 17)) (Not (Var 47)))) (And (Or (Var 25) (Or (Var 35) (Not (Var 42)))) (And (Or (Var 5) (Or (Not (Var 14)) (Not (Var 47)))) (And (Or (Not (Var 45)) (Or (Var 24) (Var 2))) (And (Or (Var 8) (Or (Not (Var 40)) (Not (Var 29)))) (And (Or (Not (Var 35)) (Or (Var 12) (Not (Var 45)))) (And (Or (Var 11) (Or (Not (Var 39)) (Not (Var 22)))) (And (Or (Not (Var 50)) (Or (Var 49) (Not (Var 6)))) (And (Or (Not (Var 37)) (Or (Not (Var 3)) (Var 5))) (And (Or (Not (Var 3)) (Or (Var 1) (Not (Var 45)))) (And (Or (Var 9) (Or (Not (Var 1)) (Var 5))) (And (Or (Not (Var 41)) (Or (Var 8) (Var 13))) (And (Or (Not (Var 42)) (Or (Var 2) (Not (Var 11)))) (And (Or (Var 24) (Or (Var 12) (Var 47))) (And (Or (Not (Var 14)) (Or (Var 7) (Not (Var 46)))) (And (Or (Var 4) (Or (Var 22) (Var 44))) (And (Or (Var 48) (Or (Not (Var 43)) (Var 21))) (And (Or (Not (Var 15)) (Or (Var 28) (Not (Var 24)))) (And (Or (Var 17) (Or (Not (Var 39)) (Not (Var 45)))) (And (Or (Var 14) (Or (Var 13) (Not (Var 6)))) (And (Or (Not (Var 48)) (Or (Var 11) (Var 49))) (And (Or (Not (Var 5)) (Or (Var 14) (Not (Var 44)))) (And (Or (Var 48) (Or (Var 39) (Var 6))) (And (Or (Not (Var 5)) (Or (Not (Var 31)) (Var 9))) (And (Or (Var 48) (Or (Var 8) (Not (Var 21)))) (And (Or (Not (Var 31)) (Or (Var 15) (Var 38))) (And (Or (Var 29) (Or (Not (Var 11)) (Not (Var 19)))) (And (Or (Var 1) (Or (Var 34) (Not (Var 31)))) (And (Or (Not (Var 27)) (Or (Var 11) (Var 25))) (And (Or (Var 44) (Or (Var 7) (Not (Var 25)))) (And (Or (Not (Var 42)) (Or (Var 41) (Var 6))) (And (Or (Var 34) (Or (Var 47) (Var 23))) (And (Or (Var 44) (Or (Var 18) (Not (Var 42)))) (And (Or (Not (Var 18)) (Or (Not (Var 1)) (Var 8))) (And (Or (Not (Var 10)) (Or (Not (Var 29)) (Not (Var 23)))) (And (Or (Not (Var 26)) (Or (Var 34) (Not (Var 23)))) (And (Or (Var 44) (Or (Not (Var 47)) (Var 38))) (And (Or (Var 25) (Or (Var 43) (Not (Var 23)))) (And (Or (Var 14) (Or (Not (Var 34)) (Not (Var 47)))) (And (Or (Var 38) (Or (Var 35) (Var 12))) (And (Or (Var 44) (Or (Not (Var 45)) (Not (Var 38)))) (And (Or (Not (Var 7)) (Or (Not (Var 20)) (Not (Var 47)))) (And (Or (Var 49) (Or (Not (Var 10)) (Var 37))) (And (Or (Var 19) (Or (Var 40) (Var 37))) (And (Or (Var 48) (Or (Var 49) (Var 9))) (And (Or (Var 3) (Or (Not (Var 11)) (Not (Var 50)))) (And (Or (Var 25) (Or (Not (Var 7)) (Not (Var 46)))) (And (Or (Not (Var 18)) (Or (Not (Var 2)) (Not (Var 27)))) (And (Or (Var 9) (Or (Not (Var 18)) (Not (Var 17)))) (And (Or (Not (Var 22)) (Or (Not (Var 28)) (Not (Var 27)))) (And (Or (Not (Var 42)) (Or (Var 40) (Not (Var 4)))) (And (Or (Not (Var 41)) (Or (Var 33) (Not (Var 47)))) (And (Or (Var 27) (Or (Var 19) (Var 40))) (And (Or (Not (Var 33)) (Or (Not (Var 17)) (Var 35))) (And (Or (Var 28) (Or (Not (Var 11)) (Not (Var 41)))) (And (Or (Not (Var 47)) (Or (Var 33) (Var 17))) (And (Or (Not (Var 41)) (Or (Var 15) (Var 7))) (And (Or (Var 25) (Or (Not (Var 28)) (Not (Var 26)))) (And (Or (Var 32) (Or (Var 14) (Not (Var 50)))) (And (Or (Var 30) (Or (Not (Var 40)) (Not (Var 50)))) (And (Or (Var 48) (Or (Not (Var 41)) (Not (Var 23)))) (And (Or (Not (Var 39)) (Or (Var 31) (Var 11))) (And (Or (Not (Var 2)) (Or (Var 42) (Var 39))) (And (Or (Var 11) (Or (Var 38) (Not (Var 32)))) (And (Or (Not (Var 50)) (Or (Var 33) (Not (Var 34)))) (And (Or (Var 40) (Or (Var 50) (Var 18))) (And (Or (Var 8) (Or (Not (Var 3)) (Var 38))) (And (Or (Var 29) (Or (Var 48) (Var 46))) (And (Or (Var 36) (Or (Not (Var 35)) (Not (Var 39)))) (And (Or (Not (Var 12)) (Or (Not (Var 44)) (Var 24))) (And (Or (Not (Var 23)) (Or (Not (Var 32)) (Not (Var 25)))) (And (Or (Not (Var 48)) (Or (Var 1) (Not (Var 41)))) (And (Or (Not (Var 39)) (Or (Var 48) (Var 35))) (And (Or (Var 35) (Or (Var 1) (Not (Var 44)))) (And (Or (Not (Var 14)) (Or (Not (Var 31)) (Var 32))) (And (Or (Not (Var 12)) (Or (Not (Var 49)) (Not (Var 6)))) (And (Or (Var 25) (Or (Var 36) (Var 1))) (And (Or (Not (Var 2)) (Or (Not (Var 9)) (Not (Var 17)))) (And (Or (Not (Var 45)) (Or (Not (Var 27)) (Not (Var 32)))) (And (Or (Var 26) (Or (Var 14) (Var 30))) (And (Or (Not (Var 31)) (Or (Not (Var 13)) (Not (Var 4)))) (And (Or (Not (Var 36)) (Or (Not (Var 23)) (Not (Var 29)))) (And (Or (Var 4) (Or (Var 39) (Not (Var 7)))) (And (Or (Not (Var 1)) (Or (Var 20) (Not (Var 27)))) (And (Or (Var 32) (Or (Not (Var 33)) (Not (Var 40)))) (And (Or (Var 17) (Or (Var 20) (Var 2))) (And (Or (Not (Var 14)) (Or (Not (Var 41)) (Var 23))) (And (Or (Not (Var 40)) (Or (Var 30) (Var 50))) (And (Or (Var 46) (Or (Not (Var 2)) (Var 44))) (And (Or (Not (Var 48)) (Or (Not (Var 15)) (Var 34))) (And (Or (Not (Var 27)) (Or (Var 43) (Not (Var 42)))) (And (Or (Var 30) (Or (Var 27) (Var 38))) (And (Or (Var 13) (Or (Var 8) (Not (Var 44)))) (And (Or (Not (Var 36)) (Or (Var 1) (Not (Var 45)))) (And (Or (Var 30) (Or (Var 21) (Var 43))) (And (Or (Var 35) (Or (Not (Var 12)) (Var 27))) (And (Or (Not (Var 43)) (Or (Var 2) (Not (Var 12)))) (And (Or (Var 8) (Or (Not (Var 28)) (Var 19))) (And (Or (Not (Var 5)) (Or (Var 33) (Not (Var 8)))) (And (Or (Not (Var 14)) (Or (Not (Var 26)) (Not (Var 29)))) (And (Or (Not (Var 12)) (Or (Not (Var 18)) (Not (Var 9)))) (And (Or (Var 12) (Or (Var 24) (Var 36))) (And (Or (Var 48) (Or (Not (Var 26)) (Var 34))) (And (Or (Not (Var 30)) (Or (Not (Var 49)) (Var 50))) (And (Or (Var 23) (Or (Var 47) (Var 31))) (And (Or (Var 48) (Or (Var 34) (Var 32))) (And (Or (Not (Var 41)) (Or (Var 33) (Var 37))) (And (Or (Var 33) (Or (Var 3) (Var 30))) (And (Or (Not (Var 33)) (Or (Not (Var 49)) (Var 23))) (And (Or (Var 37) (Or (Var 9) (Var 2))) (And (Or (Var 32) (Or (Var 8) (Not (Var 9)))) (And (Or (Var 26) (Or (Not (Var 5)) (Var 12))) (And (Or (Not (Var 17)) (Or (Not (Var 15)) (Not (Var 20)))) (And (Or (Not (Var 21)) (Or (Not (Var 14)) (Var 38))) (And (Or (Not (Var 50)) (Or (Not (Var 33)) (Not (Var 1)))) (And (Or (Not (Var 31)) (Or (Var 49) (Var 34))) (And (Or (Not (Var 19)) (Or (Not (Var 18)) (Not (Var 25)))) (And (Or (Not (Var 48)) (Or (Not (Var 15)) (Not (Var 11)))) (And (Or (Var 15) (Or (Var 10) (Var 38))) (And (Or (Var 8) (Or (Not (Var 38)) (Not (Var 44)))) (And (Or (Not (Var 34)) (Or (Not (Var 18)) (Not (Var 11)))) (And (Or (Var 15) (Or (Not (Var 5)) (Var 11))) (And (Or (Var 28) (Or (Var 7) (Var 2))) (And (Or (Not (Var 33)) (Or (Var 45) (Not (Var 25)))) (And (Or (Var 25) (Or (Not (Var 49)) (Var 41))) (And (Or (Not (Var 30)) (Or (Var 17) (Var 42))) (And (Or (Not (Var 20)) (Or (Not (Var 28)) (Var 27))) (And (Or (Not (Var 38)) (Or (Not (Var 19)) (Not (Var 30)))) (And (Or (Not (Var 7)) (Or (Var 25) (Not (Var 30)))) (And (Or (Var 14) (Or (Not (Var 37)) (Var 34))) (And (Or (Var 28) (Or (Not (Var 34)) (Not (Var 19)))) (And (Or (Var 37) (Or (Var 25) (Not (Var 17)))) (And (Or (Not (Var 4)) (Or (Not (Var 34)) (Var 18))) (And (Or (Not (Var 49)) (Or (Var 50) (Var 34))) (And (Or (Not (Var 44)) (Or (Not (Var 48)) (Var 3))) (And (Or (Not (Var 25)) (Or (Not (Var 23)) (Var 4))) (And (Or (Var 34) (Or (Not (Var 26)) (Not (Var 25)))) (And (Or (Var 39) (Or (Not (Var 45)) (Not (Var 24)))) (And (Or (Not (Var 11)) (Or (Var 37) (Var 50))) (And (Or (Var 13) (Or (Var 10) (Var 9))) (And (Or (Not (Var 35)) (Or (Not (Var 32)) (Var 27))) (And (Or (Var 40) (Or (Var 10) (Not (Var 42)))) (And (Or (Not (Var 4)) (Or (Var 49) (Var 28))) (And (Or (Not (Var 27)) (Or (Var 16) (Var 1))) (And (Or (Not (Var 37)) (Or (Not (Var 22)) (Not (Var 27)))) (And (Or (Var 49) (Or (Var 22) (Not (Var 16)))) (And (Or (Not (Var 41)) (Or (Var 49) (Var 1))) (And (Or (Not (Var 15)) (Or (Not (Var 17)) (Var 9))) (And (Or (Var 6) (Or (Not (Var 22)) (Not (Var 29)))) (And (Or (Not (Var 23)) (Or (Not (Var 34)) (Not (Var 9)))) (And (Or (Not (Var 33)) (Or (Var 26) (Not (Var 16)))) (And (Or (Not (Var 39)) (Or (Var 41) (Not (Var 25)))) (And (Or (Var 49) (Or (Not (Var 37)) (Not (Var 4)))) (And (Or (Not (Var 21)) (Or (Not (Var 34)) (Var 20))) (And (Or (Not (Var 36)) (Or (Var 13) (Not (Var 50)))) (And Yes Yes)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))


-- testFormula50d = "c This Formular is generated by mcnf\nc\nc    horn? no \nc    forced? no \nc    mixed sat? no \nc    clause length = 3 \nc\np cnf 50  218 \n 46 39 -17 0\n-40 13 35 0\n-34 -32 37 0\n31 33 -19 0\n-42 39 -20 0\n3 -14 -27 0\n-15 23 4 0\n-50 -40 -48 0\n50 -21 29 0\n-9 20 40 0\n-16 -22 21 0\n-35 6 -27 0\n-3 -4 23 0\n-47 39 32 0\n26 -15 -30 0\n-23 9 21 0\n48 37 17 0\n-7 -27 24 0\n40 -23 2 0\n32 -24 23 0\n-10 12 -25 0\n41 -2 -13 0\n28 33 -13 0\n15 1 12 0\n-23 5 33 0\n-11 25 -32 0\n12 46 39 0\n10 -30 46 0\n11 45 -8 0\n30 -33 -34 0\n34 39 -25 0\n-2 36 -25 0\n-4 -19 -6 0\n6 1 -31 0\n-43 2 24 0\n-26 48 41 0\n29 14 50 0\n-29 6 28 0\n21 11 -19 0\n41 -17 43 0\n15 18 4 0\n20 -46 -29 0\n29 26 -38 0\n-25 -30 -4 0\n-35 -21 -43 0\n-34 50 3 0\n-3 -25 15 0\n-13 -22 -38 0\n-42 -2 27 0\n22 30 29 0\n50 -40 13 0\n-22 29 -42 0\n-48 22 -7 0\n32 13 -37 0\n-16 -30 11 0\n7 -44 -6 0\n-37 17 11 0\n13 -1 42 0\n-4 -18 -26 0\n-22 -42 13 0\n49 -43 -5 0\n-49 11 47 0\n40 -14 8 0\n13 -17 -47 0\n25 35 -42 0\n5 -14 -47 0\n-45 24 2 0\n8 -40 -29 0\n-35 12 -45 0\n11 -39 -22 0\n-50 49 -6 0\n-37 -3 5 0\n-3 1 -45 0\n9 -1 5 0\n-41 8 13 0\n-42 2 -11 0\n24 12 47 0\n-14 7 -46 0\n4 22 44 0\n48 -43 21 0\n-15 28 -24 0\n17 -39 -45 0\n14 13 -6 0\n-48 11 49 0\n-5 14 -44 0\n48 39 6 0\n-5 -31 9 0\n48 8 -21 0\n-31 15 38 0\n29 -11 -19 0\n1 34 -31 0\n-27 11 25 0\n44 7 -25 0\n-42 41 6 0\n34 47 23 0\n44 18 -42 0\n-18 -1 8 0\n-10 -29 -23 0\n-26 34 -23 0\n44 -47 38 0\n25 43 -23 0\n14 -34 -47 0\n38 35 12 0\n44 -45 -38 0\n-7 -20 -47 0\n49 -10 37 0\n19 40 37 0\n48 49 9 0\n3 -11 -50 0\n25 -7 -46 0\n-18 -2 -27 0\n9 -18 -17 0\n-22 -28 -27 0\n-42 40 -4 0\n-41 33 -47 0\n27 19 40 0\n-33 -17 35 0\n28 -11 -41 0\n-47 33 17 0\n-41 15 7 0\n25 -28 -26 0\n32 14 -50 0\n30 -40 -50 0\n48 -41 -23 0\n-39 31 11 0\n-2 42 39 0\n11 38 -32 0\n-50 33 -34 0\n40 50 18 0\n8 -3 38 0\n29 48 46 0\n36 -35 -39 0\n-12 -44 24 0\n-23 -32 -25 0\n-48 1 -41 0\n-39 48 35 0\n35 1 -44 0\n-14 -31 32 0\n-12 -49 -6 0\n25 36 1 0\n-2 -9 -17 0\n-45 -27 -32 0\n26 14 30 0\n-31 -13 -4 0\n-36 -23 -29 0\n4 39 -7 0\n-1 20 -27 0\n32 -33 -40 0\n17 20 2 0\n-14 -41 23 0\n-40 30 50 0\n46 -2 44 0\n-48 -15 34 0\n-27 43 -42 0\n30 27 38 0\n13 8 -44 0\n-36 1 -45 0\n30 21 43 0\n35 -12 27 0\n-43 2 -12 0\n8 -28 19 0\n-5 33 -8 0\n-14 -26 -29 0\n-12 -18 -9 0\n12 24 36 0\n48 -26 34 0\n-30 -49 50 0\n23 47 31 0\n48 34 32 0\n-41 33 37 0\n33 3 30 0\n-33 -49 23 0\n37 9 2 0\n32 8 -9 0\n26 -5 12 0\n-17 -15 -20 0\n-21 -14 38 0\n-50 -33 -1 0\n-31 49 34 0\n-19 -18 -25 0\n-48 -15 -11 0\n15 10 38 0\n8 -38 -44 0\n-34 -18 -11 0\n15 -5 11 0\n28 7 2 0\n-33 45 -25 0\n25 -49 41 0\n-30 17 42 0\n-20 -28 27 0\n-38 -19 -30 0\n-7 25 -30 0\n14 -37 34 0\n28 -34 -19 0\n37 25 -17 0\n-4 -34 18 0\n-49 50 34 0\n-44 -48 3 0\n-25 -23 4 0\n34 -26 -25 0\n39 -45 -24 0\n-11 37 50 0\n13 10 9 0\n-35 -32 27 0\n40 10 -42 0\n-4 49 28 0\n-27 16 1 0\n-37 -22 -27 0\n49 22 -16 0\n-41 49 1 0\n-15 -17 9 0\n6 -22 -29 0\n-23 -34 -9 0\n-33 26 -16 0\n-39 41 -25 0\n49 -37 -4 0\n-21 -34 20 0\n-36 13 -50 0\n%\n0\n\n"

-- testFormula150 = "c This Formular is generated by mcnf\nc\nc    horn? no \nc    forced? no \nc    mixed sat? no \nc    clause length = 3 \nc\np cnf 150  645 \n -49 76 142 0\n-107 -24 38 0\n79 39 -117 0\n115 146 34 0\n-95 31 150 0\n-129 -108 94 0\n21 56 32 0\n93 97 -44 0\n26 125 -110 0\n60 -140 -30 0\n78 -118 -47 0\n29 108 51 0\n-66 108 15 0\n72 -44 150 0\n31 12 35 0\n150 149 -140 0\n-42 -49 35 0\n11 -25 8 0\n51 -55 68 0\n-96 117 -32 0\n-4 26 -103 0\n-70 113 -21 0\n3 -66 -5 0\n-35 143 -42 0\n123 -139 -94 0\n107 -123 146 0\n31 -35 -29 0\n32 142 -149 0\n23 -37 -83 0\n-42 -111 -115 0\n-106 -72 56 0\n17 12 57 0\n-129 -95 37 0\n-67 4 75 0\n-125 -109 -24 0\n-22 -50 60 0\n99 16 -51 0\n-50 40 59 0\n125 -84 -42 0\n-112 -57 68 0\n124 -16 62 0\n-73 43 -77 0\n-88 97 27 0\n-35 8 127 0\n-35 18 -115 0\n114 127 126 0\n86 83 111 0\n150 -145 -105 0\n71 -25 145 0\n106 -135 68 0\n30 -51 47 0\n74 12 139 0\n-42 24 40 0\n-134 121 54 0\n-28 122 -140 0\n16 -72 127 0\n-119 150 -64 0\n2 76 111 0\n-71 55 -131 0\n-129 60 120 0\n44 -21 84 0\n-74 51 11 0\n75 10 120 0\n46 -122 -97 0\n-25 75 39 0\n-6 -87 -64 0\n-100 31 48 0\n-5 -92 -65 0\n-16 23 87 0\n-91 75 109 0\n-23 75 88 0\n-84 114 -77 0\n36 79 100 0\n69 -36 3 0\n-122 -10 -144 0\n124 2 -83 0\n-144 130 -54 0\n-10 132 34 0\n25 -103 82 0\n63 105 -27 0\n-51 -29 -107 0\n111 83 102 0\n12 67 136 0\n92 -51 -122 0\n41 140 -58 0\n-23 -96 -142 0\n101 39 13 0\n57 -64 137 0\n61 51 -63 0\n136 116 130 0\n-7 55 122 0\n-78 135 -88 0\n-11 -93 54 0\n9 -44 -64 0\n61 -62 -103 0\n67 -111 41 0\n87 -37 -58 0\n14 -137 36 0\n-80 142 -64 0\n-130 124 50 0\n-68 -81 116 0\n-32 -54 -110 0\n33 91 73 0\n88 -87 -48 0\n140 -59 -83 0\n45 58 -27 0\n83 -47 -48 0\n129 -18 67 0\n108 24 -10 0\n114 14 -147 0\n143 -98 45 0\n13 -40 -106 0\n-36 -61 109 0\n25 70 -68 0\n-123 -38 106 0\n-106 -77 107 0\n60 107 104 0\n106 52 97 0\n108 28 129 0\n117 34 91 0\n81 -108 100 0\n101 18 2 0\n90 139 70 0\n95 10 101 0\n126 1 46 0\n90 4 -7 0\n-84 142 132 0\n103 135 3 0\n95 116 -65 0\n-57 -14 100 0\n1 18 26 0\n-121 140 -57 0\n-117 27 -87 0\n-24 144 -73 0\n-37 96 124 0\n8 48 -70 0\n99 -25 116 0\n108 93 -67 0\n-3 85 -109 0\n37 59 -93 0\n-63 -53 -37 0\n108 34 -116 0\n112 148 -35 0\n-144 -45 32 0\n100 6 113 0\n31 78 -60 0\n-9 -17 29 0\n-67 -51 -66 0\n-48 73 -3 0\n-133 125 -128 0\n104 -47 -71 0\n8 -124 -147 0\n106 -14 136 0\n-130 -13 138 0\n-103 75 137 0\n-73 -124 49 0\n-123 144 -136 0\n54 136 98 0\n-104 -137 75 0\n-104 -71 -92 0\n-92 73 85 0\n-4 37 -65 0\n73 -59 -82 0\n82 -51 75 0\n-24 96 -113 0\n76 -127 -34 0\n-82 -121 -136 0\n92 32 -49 0\n112 -134 48 0\n79 -14 135 0\n3 54 -146 0\n-135 -145 83 0\n111 -82 -74 0\n6 -67 -109 0\n-92 32 -112 0\n-96 -75 143 0\n-55 96 51 0\n-30 27 -123 0\n79 -43 -144 0\n-135 -37 127 0\n36 -59 -123 0\n-84 55 -29 0\n-25 71 121 0\n74 -102 -49 0\n-13 123 -31 0\n39 -105 52 0\n-94 67 -106 0\n66 75 -68 0\n-43 145 44 0\n-84 74 4 0\n107 -102 28 0\n61 56 -77 0\n-14 -94 -51 0\n23 -22 116 0\n-97 45 101 0\n24 -116 -115 0\n-61 35 133 0\n114 -64 -104 0\n-136 -17 104 0\n-128 -29 -110 0\n92 3 84 0\n-133 -115 -92 0\n-125 -66 56 0\n-10 65 -67 0\n28 143 -137 0\n12 10 -39 0\n51 -28 38 0\n140 -45 -86 0\n77 38 54 0\n67 -46 -80 0\n9 128 96 0\n143 -96 37 0\n-61 100 60 0\n133 -94 -71 0\n88 -50 -19 0\n105 112 50 0\n1 103 -96 0\n-92 12 20 0\n-71 -122 -123 0\n44 -4 -114 0\n16 -68 60 0\n125 -77 -19 0\n30 -49 -93 0\n102 57 92 0\n-19 -57 49 0\n-80 134 -73 0\n55 -24 75 0\n-4 123 81 0\n66 124 -123 0\n-52 67 43 0\n105 -128 144 0\n-25 -22 67 0\n132 99 -62 0\n-111 128 -101 0\n-20 -91 -129 0\n-74 -117 134 0\n126 104 -93 0\n-57 147 -84 0\n96 -2 -65 0\n-134 -139 30 0\n-102 -31 135 0\n111 107 21 0\n-5 88 -66 0\n-25 1 -109 0\n28 -31 66 0\n76 95 54 0\n-128 140 142 0\n-68 -47 111 0\n90 -10 17 0\n126 -95 42 0\n108 33 118 0\n-145 -52 144 0\n61 -141 -126 0\n133 -135 7 0\n8 -58 -16 0\n-113 47 136 0\n82 60 99 0\n91 113 33 0\n57 139 142 0\n-135 27 131 0\n-104 -38 117 0\n-137 -49 -91 0\n127 -65 -106 0\n17 -37 -100 0\n82 -85 145 0\n-132 -39 107 0\n130 114 -122 0\n64 25 -10 0\n-130 50 -27 0\n48 139 -62 0\n111 -32 35 0\n-141 110 125 0\n58 -93 -47 0\n-56 92 129 0\n-59 -68 25 0\n117 -71 -106 0\n-12 -128 45 0\n9 147 -17 0\n-136 119 -70 0\n150 -109 -7 0\n98 45 37 0\n140 57 -1 0\n-108 -52 -86 0\n102 92 117 0\n-110 -56 126 0\n-83 -28 -98 0\n-143 -70 -49 0\n83 62 -143 0\n-18 137 -42 0\n-2 -118 -3 0\n-31 -18 109 0\n121 -129 110 0\n-111 55 125 0\n-54 -91 147 0\n42 77 122 0\n-127 84 74 0\n-126 32 39 0\n-149 -12 -65 0\n-133 -19 79 0\n-134 6 -81 0\n-12 -27 -67 0\n145 87 10 0\n-43 -20 73 0\n95 -125 57 0\n-28 87 -26 0\n92 -54 102 0\n-136 135 150 0\n-57 60 41 0\n17 -112 -8 0\n-94 -14 -48 0\n-44 63 -144 0\n59 57 -118 0\n-80 -108 44 0\n3 104 23 0\n121 -120 -22 0\n-108 -133 -55 0\n85 -37 -32 0\n-36 -25 -40 0\n141 147 -80 0\n22 -127 76 0\n-35 103 -148 0\n-65 139 -12 0\n28 77 -131 0\n-45 147 -121 0\n80 32 -104 0\n20 108 -51 0\n143 112 -93 0\n-112 85 60 0\n67 47 62 0\n-15 -100 103 0\n-66 -125 135 0\n71 -134 143 0\n147 100 -135 0\n121 -109 34 0\n105 -11 -3 0\n84 44 81 0\n-99 -80 57 0\n-142 -89 145 0\n-113 -115 -144 0\n49 102 -150 0\n-7 93 22 0\n10 109 111 0\n-110 42 -143 0\n-140 -130 -102 0\n-123 23 51 0\n-100 80 3 0\n-2 -26 122 0\n16 51 -64 0\n-145 60 96 0\n101 -57 96 0\n-22 58 8 0\n-144 100 143 0\n-121 -92 79 0\n122 91 -69 0\n112 -19 -9 0\n62 -112 -46 0\n-91 97 -70 0\n98 -22 -52 0\n-35 122 89 0\n56 1 -26 0\n-52 119 78 0\n67 129 -136 0\n9 53 -148 0\n69 24 -85 0\n-76 -63 -118 0\n-42 -88 11 0\n56 106 21 0\n-138 26 104 0\n132 -128 -29 0\n-8 75 -3 0\n58 -106 60 0\n-111 150 142 0\n-32 28 -34 0\n141 144 71 0\n-110 68 144 0\n-84 101 -14 0\n30 -129 -107 0\n29 -142 25 0\n-6 -117 -31 0\n-146 95 8 0\n47 -142 1 0\n-18 14 -149 0\n-122 -63 99 0\n33 130 42 0\n3 51 122 0\n61 -87 20 0\n-81 -15 18 0\n-36 -111 -115 0\n-60 139 -68 0\n-128 54 24 0\n-128 124 -150 0\n2 115 -12 0\n72 79 111 0\n125 123 -55 0\n15 52 9 0\n-101 -129 -46 0\n-98 -128 -45 0\n109 -69 -16 0\n135 -79 -52 0\n145 135 26 0\n-75 123 -5 0\n-50 -22 -108 0\n33 89 -24 0\n128 142 57 0\n4 26 12 0\n56 103 -7 0\n-40 123 -102 0\n-102 -100 20 0\n104 125 19 0\n37 7 -75 0\n-82 92 -55 0\n-18 42 99 0\n50 -141 -115 0\n-96 -69 -87 0\n-13 116 -96 0\n-40 95 -74 0\n71 50 117 0\n-35 -68 -146 0\n112 82 -30 0\n-138 -58 -74 0\n-66 -34 31 0\n65 48 -113 0\n37 -103 48 0\n144 -64 115 0\n131 100 67 0\n140 -99 94 0\n84 2 119 0\n26 -70 -138 0\n107 -96 -4 0\n-81 99 -64 0\n57 142 -45 0\n72 -96 134 0\n76 -17 87 0\n4 -46 -135 0\n122 47 52 0\n132 -100 46 0\n-8 21 -4 0\n-8 136 -12 0\n-134 53 -148 0\n-71 30 11 0\n25 47 -3 0\n-128 80 123 0\n-127 79 19 0\n-91 -7 120 0\n52 46 -59 0\n-116 -43 -20 0\n71 91 -21 0\n-77 49 19 0\n-13 128 49 0\n11 117 -69 0\n43 -145 -129 0\n3 -34 -32 0\n-114 -4 3 0\n25 -111 -18 0\n96 104 -49 0\n-102 -66 71 0\n22 130 -67 0\n8 -117 -147 0\n50 124 -55 0\n149 142 -101 0\n123 108 39 0\n-77 -60 -145 0\n-136 -121 114 0\n-78 -30 -37 0\n-130 -95 -75 0\n-53 114 -39 0\n-107 -84 -136 0\n98 62 70 0\n126 -122 80 0\n95 83 -122 0\n-100 66 -77 0\n65 113 -17 0\n150 12 5 0\n119 49 -20 0\n76 4 56 0\n-10 -122 -134 0\n20 24 103 0\n-129 -74 -28 0\n32 111 149 0\n-25 -85 -62 0\n-149 -142 56 0\n123 -97 -40 0\n-92 -113 37 0\n69 127 -140 0\n125 -52 84 0\n121 -130 -57 0\n-42 84 81 0\n-45 100 -26 0\n-109 136 -98 0\n97 28 27 0\n96 35 -138 0\n136 103 32 0\n130 78 139 0\n127 117 -42 0\n-50 12 122 0\n86 -138 -71 0\n22 126 -84 0\n-94 22 45 0\n139 -4 -20 0\n-125 128 -96 0\n133 140 -126 0\n-34 -84 -91 0\n-85 81 4 0\n33 1 -34 0\n-136 -6 -89 0\n69 -85 134 0\n-10 -21 -130 0\n-83 74 48 0\n117 -86 -60 0\n112 123 96 0\n44 124 -133 0\n74 -27 -140 0\n20 -60 -52 0\n127 -113 40 0\n127 -75 150 0\n-120 20 27 0\n72 120 71 0\n-40 -43 -107 0\n-45 -86 66 0\n-110 98 -104 0\n12 -140 -98 0\n82 14 -114 0\n49 114 -29 0\n108 98 74 0\n53 -141 144 0\n85 -111 -4 0\n-26 -81 110 0\n125 -131 148 0\n142 -94 149 0\n-111 19 -20 0\n-118 -109 -78 0\n68 16 -7 0\n60 -129 69 0\n-108 124 -148 0\n136 -1 133 0\n123 73 -116 0\n-128 -112 -121 0\n-72 -48 -104 0\n45 62 -60 0\n-7 4 100 0\n-148 132 126 0\n69 -10 -131 0\n-14 65 -16 0\n-53 -100 32 0\n62 -149 53 0\n65 -136 43 0\n60 17 -84 0\n10 69 140 0\n145 89 -144 0\n-75 -113 -136 0\n-38 110 80 0\n138 -76 88 0\n38 -49 3 0\n-57 23 41 0\n-7 37 -13 0\n-21 -48 96 0\n105 -113 80 0\n55 -29 109 0\n-104 -149 -66 0\n22 87 27 0\n-20 90 85 0\n121 145 22 0\n110 -90 -42 0\n111 -101 132 0\n17 117 148 0\n81 -21 7 0\n-74 107 -42 0\n109 115 17 0\n-135 144 114 0\n28 -37 25 0\n-92 10 46 0\n146 99 -139 0\n-114 4 -110 0\n-144 -138 135 0\n16 131 -41 0\n-66 98 131 0\n-144 -42 -104 0\n-127 43 1 0\n79 -17 -143 0\n-68 141 -77 0\n80 97 -30 0\n65 52 118 0\n15 -11 -89 0\n20 -26 -129 0\n109 -7 -93 0\n-118 -44 -70 0\n74 18 30 0\n89 50 76 0\n-139 -85 -48 0\n69 -56 -142 0\n135 59 -1 0\n33 130 121 0\n127 -110 -55 0\n-74 -125 55 0\n-107 11 -58 0\n56 7 -58 0\n-9 93 -94 0\n135 131 76 0\n9 -106 -37 0\n-65 -33 139 0\n122 -37 -16 0\n-143 -101 19 0\n-52 -64 4 0\n-39 111 140 0\n54 89 -99 0\n52 33 117 0\n144 -54 -10 0\n36 43 -3 0\n73 -58 -66 0\n-129 -37 -27 0\n-7 131 120 0\n33 42 -85 0\n-131 -89 -118 0\n89 -50 45 0\n-94 91 -65 0\n58 -24 124 0\n-59 30 -64 0\n68 53 57 0\n22 -125 83 0\n94 73 136 0\n-2 -101 27 0\n147 37 -53 0\n-27 -98 26 0\n117 4 36 0\n-95 14 -88 0\n-83 -24 81 0\n132 146 -95 0\n8 82 71 0\n-95 131 -58 0\n-145 124 141 0\n-63 -137 37 0\n-52 -77 -30 0\n120 118 16 0\n94 95 11 0\n-128 70 14 0\n132 64 -54 0\n-52 -108 75 0\n16 -73 2 0\n62 57 96 0\n-113 36 -90 0\n-44 136 6 0\n96 -55 -20 0\n54 3 47 0\n57 96 -67 0\n-23 -130 10 0\n%\n0\n\n"