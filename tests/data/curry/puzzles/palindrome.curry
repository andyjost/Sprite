isPalindrome :: Int -> Bool
isPalindrome x = let s = show x in s == reverse s

main =  isPalindrome 1
     && isPalindrome 121
     && isPalindrome 45833854
     && not (isPalindrome (-1))
     && not (isPalindrome 10)
     && not (isPalindrome 1010)
