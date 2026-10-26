{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}
{-# OPTIONS_CYMAKE -Wnone #-} -- no warnings

----------------------------------------------------------------------
-- imported from Cards:
data Suit = Club | Spade | Heart | Diamond 
 deriving Eq

data Rank = Ace | King | Queen | Jack | Ten | Nine | Eight
          | Seven | Six | Five | Four | Three | Two 
 deriving Eq

data Card = Card Rank Suit
 deriving Eq

rank (Card r _) = r
suit (Card _ s) = s
----------------------------------------------------------------------

isFour (x++[_]++z) | map rank (x++z) == [r,r,r,r] = Just r where r free
isFour'default _ = Nothing

main = (isFour testYes, isFour testNo)

testYes = [(Card Six Club),(Card Six Spade),(Card Five Heart),
           (Card Six Heart),(Card Six Diamond)]
testNo  = [(Card Six Club),(Card Ace Spade),(Card Five Heart),
           (Card Ace Club),(Card Six Diamond)]

