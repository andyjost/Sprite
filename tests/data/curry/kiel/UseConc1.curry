import ModConc hiding ((+))  -- prelude.+ should still be visible

goal1 :: [Int]
goal1 = [1] .+. [1+1]

goal2 :: [Int]
goal2 = [1] ModConc..+. [1+1]

goal3 :: [Int]
goal3 = conc [1] [2]
