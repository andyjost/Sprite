{-# OPTIONS_CYMAKE -F --pgmF=currypp --optF=defaultrules #-}
{-# OPTIONS_CYMAKE -Wnone #-} -- no warnings

----------------------------------------------------------------------
--import Cards
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

isFullHouse (x++[a]++y++[b]++z)
  | map rank (x++y++z) == [r,r,r] && rank a == rank b
  = Just r
  where r free
isFullHouse'default _ = Nothing

testYes = [(Card Ace Club),(Card Two Spade),(Card Ace Heart),
           (Card Two Heart),(Card Two Diamond)]
testNo  = [(Card Six Club),(Card Ace Spade),(Card Five Heart),
           (Card Ace Club),(Card Six Diamond)]
main = (isFullHouse testYes, isFullHouse testNo)


