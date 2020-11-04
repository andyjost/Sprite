-- A few examples to test the notation for arithmetic sequences:

goal1 :: [Int]
goal1 = [1..20]
--> [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]

goal2 :: [Int]
goal2 = take 20 [1..]
-->  [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]

goal3 :: [Int]
goal3 = [1,5..100]
--> [1,5,9,13,17,21,25,29,33,37,41,45,49,53,57,61,65,69,73,77,81,85,89,93,97]

goal4 :: [Int]
goal4 = take 20 [1,5..]
--> [1,5,9,13,17,21,25,29,33,37,41,45,49,53,57,61,65,69,73,77]

