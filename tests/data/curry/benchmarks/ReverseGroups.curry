-- Given a linked list, reverse the nodes of a linked list k at a time and return
-- its modified list.
--
-- k is a positive integer and is less than or equal to the length of the linked
-- list. If the number of nodes is not a multiple of k then left-out nodes, in the
-- end, should remain as it is.
--
-- You may not alter the values in the list's nodes, only nodes themselves may be
-- changed.

kreverse k xs = let (h,t) = (take k xs, drop k xs) in
    if length h == k then reverse h ++ kreverse k t else h

isList [] = True
isList (_:xs) = isList xs

main :: [Bool]
main = [isList (kreverse i [1..5000]) | i <- [1..50]]
-- main =  kreverse 1 "" == ""
--      && kreverse 1 "abc" == "abc"
--      && kreverse 2 "abc" == "bac"
--      && kreverse 2 [1,2,3,4,5] == [2,1,4,3,5]
--      && kreverse 3 [1,2,3,4,5] == [3,2,1,4,5]
