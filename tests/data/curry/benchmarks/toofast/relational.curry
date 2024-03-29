-- Module Relational from the Escher paper:
-- computing with relations

data Person = Bob | John | Mary | Sue | Dick | Kate | Ned

parent Bob  John = True
parent Bob  Dick = True
parent John Mary = True
parent Sue  Dick = True
parent Dick Kate = True

age Bob  = 24
age John = 7
age Mary = 13
age Sue  = 23
age Dick = 53
age Kate = 11
age Ned  = 23


mappred _ [] [] = True
mappred p (x:xs) (y:ys) | p x y && mappred p xs ys  = True

con2bool c | c = True


forevery _ [] = True
forevery c (x:xs) | c x = forevery c xs

-- Queries:
goal1 :: [Int]
goal1 = map age [Bob,Sue]   --> [24,23]

goal2 x = mappred parent [Bob,Dick] x
--> {x=[john,kate]} true | {x=[dick,kate]} true

goal3 r = mappred r [Bob,Sue] [24,23]
--> r(bob,24) /\ r(sue,23)

goal4 w = mappred (\x y -> con2bool (age x =:= y)) w [24,23]
--> {w=[bob,sue]} true | {w=[bob,ned]} true

goal5 y = forevery (\x -> age x =:= y) [Ned,Bob,Sue]
--> no solution

goal6 y = forevery (\x -> age x =:= y) [Ned,Sue]
--> {y=23} true

goal7 :: Bool
goal7 = forevery (\x -> let y free in age x =:= y) [Ned,Bob,Sue]
--> true

main = (goal1, goal2, goal3, goal4, goal6, goal7)
