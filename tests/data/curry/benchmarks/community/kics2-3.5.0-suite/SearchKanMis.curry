
-- Anzahl der Kannibalen und Missionare
type SingleState = (Int, Int)

-- Fahrtrichtung des Bootes
data Direction = Forward | Backward

-- Gesamtzustand: Anzahl linkes Ufer, Anzahl rechtes Ufer, Bootsrichtung
type GlobalState = (SingleState, SingleState, Direction)

find :: Int -> Int -> [GlobalState]
find n m = findRoute (startState n m) (endState n m) []

findRoute :: GlobalState -> GlobalState -> [GlobalState] -> [GlobalState]
findRoute start end route
  | start == end          = reverse (end:route)
  | start `notElem` route = findRoute (nextState start) end (start:route)

startState :: Int -> Int -> GlobalState
startState n m = ((n, m), (0, 0), Forward)

endState :: Int -> Int -> GlobalState
endState n m = ((0, 0), (n, m), Backward)

nextState :: GlobalState -> GlobalState
nextState ((lk,lm),(rk,rm),Forward)
  | ((movingMissos + movingKanibs) `elem` [1,2]) =:= True
  & ((lk - movingKanibs) >= 0) =:= True
  & (lm - movingMissos) `isGeqOrZero` (lk - movingKanibs)
  & (rm + movingMissos) `isGeqOrZero` (rk + movingKanibs)
  = ( (lk - movingKanibs, lm - movingMissos)
    , (rk + movingKanibs, rm + movingMissos)
    , Backward )
  where
    movingKanibs = zeroOrOneOrTwo
    movingMissos = zeroOrOneOrTwo
nextState ((lk,lm),(rk,rm),Backward)
  | ((movingMissos + movingKanibs) `elem` [1,2]) =:= True
  & ((rk - movingKanibs) >= 0) =:= True
  & (rm - movingMissos) `isGeqOrZero` (rk - movingKanibs)
  & (lm + movingMissos) `isGeqOrZero` (lk + movingKanibs)
  = ( (lk + movingKanibs, lm + movingMissos)
    , (rk - movingKanibs, rm - movingMissos)
    , Forward )
  where
    movingKanibs = zeroOrOneOrTwo
    movingMissos = zeroOrOneOrTwo

isGeqOrZero :: Int -> Int -> Success
isGeqOrZero n m | n == 0 || n >= m = success

zeroOrOneOrTwo :: Int
zeroOrOneOrTwo = 0 ? 1 ? 2

main = find 50 51