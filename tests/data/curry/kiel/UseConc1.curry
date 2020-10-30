import ModConc hiding ((+))  -- prelude.+ should still be visible

goal1 = [1] .+. [1+1]
goal2 = [1] ModConc..+. [1+1]
goal3 = conc [1] [2]

main :: ([Int], [Int], [Int])
main = (goal1, goal2, goal3)
