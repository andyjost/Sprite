isPalindrome :: Int -> Bool
isPalindrome x = let s = show x in s == reverse s

main =  map isPalindrome [1..1000]
